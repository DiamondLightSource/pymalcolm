# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types, Anno, TYPE_CHECKING
from scanpointgenerator import Point

from malcolm.core import APartName, Block, Attribute, Context, PartRegistrar
from malcolm.modules import builtin, scanning, pmac
from malcolm.modules.pmac.infos import MotorInfo

from ..util import SequencerTable, Trigger

if TYPE_CHECKING:
    from typing import List, Tuple, Dict

#: The SEQ.table attributes that should be present in PANDA.exports
SEQ_TABLES = ("seqTableA", "seqTableB")

#: The number of sequencer table rows
SEQ_TABLE_ROWS = 4096

with Anno("Scannable name for sequencer input"):
    APos = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

# How long is a single tick if prescaler is 0
TICK = 8e-9

# Minimum number of ticks for a phase to generate a reasonable length pulse
# that might travel over ttl
MIN_PHASE = 125  # 125 ticks = 1 us

# Maximum repeats of a single row
MAX_REPEATS = 4096


def seq_row(repeats=1, trigger=Trigger.IMMEDIATE, position=0,
            half_duration=MIN_PHASE, live=0, dead=0):
    # type: (int, str, int, int, int, int) -> List
    """Create a 50% duty cycle pulse with phase1 having given live/dead values
    """
    row = [repeats, trigger, position,
           # Phase1
           half_duration, live, dead, 0, 0, 0, 0,
           # Phase2
           half_duration, 0, 0, 0, 0, 0, 0]
    return row


def _get_blocks(context, panda_mri):
    # type: (Context, str) -> List[Block]
    """Get panda, seqA and seqB Blocks using the given context"""
    # {part_name: export_name}
    panda = context.block_view(panda_mri)
    seq_part_names = {}
    for source, export in panda.exports.value.rows():
        if export in SEQ_TABLES:
            assert source.endswith(".table"), \
                "Expected export %s to come from SEQx.table, got %s" % (
                    export, source)
            seq_part_names[source[:-len(".table")]] = export
    assert tuple(sorted(seq_part_names.values())) == SEQ_TABLES, \
        "Expected exported attributes %s, got %s" % (
            SEQ_TABLES, panda.exports.value.export)
    # {export_name: mri}
    seq_mris = {}
    for name, mri, _, _, _ in panda.layout.value.rows():
        if name in seq_part_names:
            export = seq_part_names[name]
            seq_mris[export] = mri
    assert sorted(seq_mris) == sorted(seq_part_names.values()), \
        "Couldn't find MRI for some of %s" % (seq_part_names.values(),)
    blocks = [panda]
    blocks += [context.block_view(seq_mris[x]) for x in SEQ_TABLES]
    return blocks


def _what_moves_most(point, axis_mapping):
    # type: (Point, Dict[str, MotorInfo]) -> Tuple[str, int, bool]
    """Work out which axis from the given axis mapping moves most for this
    point"""
    # TODO: should use new velocity calcs when Giles has finished
    # {axis_name: abs(diff_cts)}
    diffs = {}
    # {axis_name: (compare_cts, increasing)}
    compare_increasing = {}
    for s, info in axis_mapping.items():
        compare_cts = info.in_cts(point.lower[s])
        centre_cts = info.in_cts(point.positions[s])
        diff_cts = centre_cts - compare_cts
        if diff_cts != 0:
            diffs[s] = abs(diff_cts)
            compare_increasing[s] = (compare_cts, diff_cts > 0)
    assert diffs, \
        "Can't work out a compare point for %s, maybe none of the axes " \
        "connected to the PandA are moving during the scan point?" % \
        point.positions
    # Sort on abs(diff), take the biggest
    axis_name = sorted(diffs, key=diffs.get)[-1]
    compare_cts, increasing = compare_increasing[axis_name]
    return axis_name, compare_cts, increasing


class PandAPcompPart(builtin.parts.ChildPart):
    """Part for operating a pair of SEQ blocks in a PandA to do position
    compare"""

    def __init__(self, name, mri, initial_visibility=None):
        # type: (APartName, AMri, AInitialVisibility) -> None
        super(PandAPcompPart, self).__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False)
        # Stored generator for positions
        self.generator = None
        # The last index we have loaded
        self.loaded_up_to = 0
        # The last scan point index of the current run
        self.scan_up_to = 0
        # If we are currently loading then block loading more points
        self.loading = False
        # The last point we loaded
        self.last_point = None
        # What is the mapping of scannable name to MotorInfo
        self.axis_mapping = {}
        # The minimum turnaround time for non-joined points
        self.min_turnaround = 0
        # {(scannable, increasing): trigger_enum}
        self.trigger_enums = {}
        # The panda Block we will be prodding
        self.panda = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandAPcompPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.configure)
        registrar.hook(scanning.hooks.RunHook, self.run)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove  # type: scanning.hooks.AAxesToMove
                  ):
        # type: (...) -> None
        self.generator = generator
        self.loaded_up_to = completed_steps
        self.scan_up_to = completed_steps + steps_to_do
        self.loading = False
        self.last_point = None

        # Get the panda and the pmac we will be using
        panda_mri = context.block_view(self.mri).panda.value
        pmac_mri = context.block_view(self.mri).pmac.value

        # See if there is a minimum turnaround
        infos = scanning.infos.MinTurnaroundInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, \
                "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(infos)
            self.min_turnaround = max(pmac.util.MIN_TIME, infos[0].gap)
        else:
            self.min_turnaround = pmac.util.MIN_TIME

        # Get panda Block, and the sequencer Blocks so we can do some checking
        self.panda, seqa, seqb = _get_blocks(context, panda_mri)

        # Check that both sequencers are pointing to the same encoders
        seq_pos = {}
        for suff in "abc":
            # Something like INENC1.VAL or ZERO
            seqa_pos_inp = seqa["pos" + suff].value
            seqb_pos_inp = seqb["pos" + suff].value
            assert seqa_pos_inp == seqb_pos_inp, \
                "SeqA Pos%s = %s != SeqB Pos%s = %s" % (
                    suff, seqa_pos_inp, suff, seqb_pos_inp)
            seq_pos[seqa_pos_inp] = "POS%s" % suff.upper()

        # Fill in motor infos and trigger lookups
        motion_axes = pmac.util.get_motion_axes(generator, axesToMove)
        self.axis_mapping = {}
        self.trigger_enums = {}
        if motion_axes:
            # We need to do a compare, so only place the infos into the
            # axis_mapping that our sequencer can see
            axis_mapping = pmac.util.cs_axis_mapping(
                context, context.block_view(pmac_mri).layout.value, motion_axes)
            # Fix the mres and offsets from the panda positions table
            positions_table = self.panda.positions.value
            for i, name in enumerate(positions_table.name):
                try:
                    pos = seq_pos[name]
                except KeyError:
                    # This is a position not connected to the seq, this is fine
                    pass
                else:
                    # This is a position that we can compare on, check its
                    # dataset name which is the scannable name
                    scannable = positions_table.datasetName[i]
                    info = axis_mapping.get(scannable, None)
                    if info:
                        # We are asked to scan this, so correct its resolution
                        # and store
                        info.resolution = positions_table.scale[i]
                        info.offset = positions_table.offset[i]
                        self.axis_mapping[scannable] = info
                        self.trigger_enums[(scannable, True)] = \
                            "%s>=POSITION" % pos
                        self.trigger_enums[(scannable, False)] = \
                            "%s<=POSITION" % pos
            # Check we have at least one entry
            assert self.axis_mapping, \
                "None of the seq inputs %s can be mapped to scannable names " \
                "in %s. Did you define datasetName entries for these rows in " \
                "the PandA positions table?" % (sorted(seq_pos), motion_axes)

        # TODO:
        # Check that the sequencer blocks have the correct wiring, delays, and
        # setup monitors on the active field
        assert seqa
        assert seqb

        # load up the first SEQ
        self._fill_sequencer(self.panda[SEQ_TABLES[0]])

    def _how_long_moving_wrong_way(self, axis_name, point, increasing):
        # type: (str, Point, bool) -> float
        """Work out the turnaround for the axis with the given MotorInfo, and
        how long it is moving in the opposite direction from where we want it to
        be going for point"""
        time_arrays, velocity_arrays = pmac.util.profile_between_points(
            self.axis_mapping, self.last_point, point, self.min_turnaround)
        info = self.axis_mapping[axis_name]
        time_array = time_arrays[info.scannable]
        velocity_array = velocity_arrays[info.scannable]

        # Work backwards through the velocity array until we are going the
        # opposite way
        i = 0
        for i, v in reversed(list(enumerate(velocity_array))):
            # Divide v by resolution so it is in counts
            v /= info.resolution
            if (increasing and v <= 0) or (not increasing and v >= 0):
                # The axis is stationary or going the wrong way at this
                # point, so we should be blind before then
                assert i < len(velocity_array) - 1, \
                    "Last point of %s is wrong direction" % velocity_array
                break
        blind = time_array[i]
        return blind

    def _fill_sequencer(self, seq_table):
        # type: (Attribute) -> None
        rows = []
        for i in range(self.loaded_up_to, self.scan_up_to):
            point = self.generator.get_point(i)
            half_frame = int(round(point.duration / TICK / 2))
            if self.axis_mapping and (
                    self.last_point is None or not pmac.util.points_joined(
                    self.axis_mapping, self.last_point, point)):
                # First row, or rows not joined
                # Work out which axis moves most during this point
                axis_name, compare_cts, increasing = _what_moves_most(
                    point, self.axis_mapping)
                # If we have a previous point, how long to be blind for during
                # the turnaround
                if self.last_point is not None:
                    blind = self._how_long_moving_wrong_way(
                        axis_name, point, increasing)
                    half_blind = int(round(blind / TICK / 2))
                    rows.append(seq_row(half_duration=half_blind, dead=1))
                # Create a compare point for the next row
                trigger_enum = self.trigger_enums[(axis_name, increasing)]
                rows.append(seq_row(
                    trigger=trigger_enum, position=compare_cts,
                    half_duration=half_frame, live=1))
            elif rows and rows[-1][1] == Trigger.IMMEDIATE and \
                    rows[-1][3] == half_frame and rows[-1][0] < MAX_REPEATS:
                # Repeated time row, just increment the last row repeats
                rows[-1][0] += 1
            else:
                # New time section
                rows.append(seq_row(half_duration=half_frame, live=1))
            if i == self.scan_up_to - 1:
                # Last row, one last dead frame signal
                rows.append(seq_row(dead=1))
            self.last_point = point
            if len(rows) > SEQ_TABLE_ROWS - 3:
                # If we don't have enough space for more rows, stop here
                break

        table = SequencerTable.from_rows(rows)
        seq_table.put_value(table)

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Call sequence table enable
        self.panda.seqSetEnable()
