# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types, Anno, TYPE_CHECKING
from scanpointgenerator import Point

from malcolm.core import APartName, Block, Attribute, Context, PartRegistrar
from malcolm.modules import builtin, scanning, pmac

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

# How long is the smallest pulse that will travel across TTL
MIN_PULSE = 1250  # ticks = 10us

# How long the last pulse should be (50% duty cycle) to make sure we don't flip
# to an unfilled sequencer and produce a false pulse. This should be at least
# as long as it takes the PandA EPICS driver to see that we got the last frame
# and disarm PCAP
LAST_PULSE = 125000000  # ticks = 1s

# Maximum repeats of a single row
MAX_REPEATS = 4096


def seq_row(repeats=1, trigger=Trigger.IMMEDIATE, position=0,
            half_duration=MIN_PULSE, live=0, dead=0):
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
    # type: (Point, Dict[str, pmac.infos.MotorInfo]) -> Tuple[str, int, bool]
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


def doing_pcomp(row_trigger_value):
    # type: (str) -> bool
    return row_trigger_value == "Position Compare"


class PandASeqTriggerPart(builtin.parts.ChildPart):
    """Part for operating a pair of SEQ blocks in a PandA to do position
    compare at the start of each row and time based pulses within the row.
    Needs the following exports:

    - seqTableA: table Attribute of the first SEQ block
    - seqTableB: table Attribute of the second SEQ block
    - seqSetEnable: forceSet Method of an SRGATE that is used to gate both SEQs
    """

    def __init__(self, name, mri, initial_visibility=None):
        # type: (APartName, AMri, AInitialVisibility) -> None
        super(PandASeqTriggerPart, self).__init__(
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
        super(PandASeqTriggerPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.report_status)
        registrar.hook(scanning.hooks.ConfigureHook, self.configure)
        registrar.hook(scanning.hooks.RunHook, self.run)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        # Work out if we need the motor controller to send start of row triggers
        # or no triggers
        if doing_pcomp(child.rowTrigger.value):
            # Doing position compare, don't need any triggers
            trigger = scanning.infos.MotionTrigger.NONE
        else:
            # Waiting for bit at the start of each row, so need this signal
            trigger = scanning.infos.MotionTrigger.ROW_GATE
        info = scanning.infos.MotionTriggerInfo(trigger)
        return info

    def setup_pcomp_dicts(self, seqa, seqb, axis_mapping):
        """Setup the axis_mapping and trigger_enum dicts for position compare"""
        # type: (Block, Block, Dict[str, pmac.infos.MotorInfo]) -> None
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
            "the PandA positions table?" % (
                sorted(seq_pos), sorted(axis_mapping))

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
        child = context.block_view(self.mri)
        panda_mri = child.panda.value
        pmac_mri = child.pmac.value
        row_trigger = child.rowTrigger.value

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

        # Fill in motor infos and trigger lookups
        motion_axes = pmac.util.get_motion_axes(generator, axesToMove)
        self.axis_mapping = {}
        self.trigger_enums = {}

        if motion_axes:
            # Need to fill in the axis mapping
            axis_mapping = pmac.util.cs_axis_mapping(
                context, context.block_view(pmac_mri).layout.value, motion_axes)
            if doing_pcomp(row_trigger):
                # We need to do position compare, so only place the infos into
                # axis_mapping that our sequencer can see
                self.setup_pcomp_dicts(seqa, seqb, axis_mapping)
            else:
                # We rely on the inputs coming into SEQ bitA
                assert seqa["bita"].value == seqb["bita"].value != "ZERO", \
                    "SEQ.bita inputs need to point to the same non-zero input"
                self.axis_mapping = axis_mapping

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
            start_of_row = False
            if self.axis_mapping:
                if self.last_point is None or not pmac.util.points_joined(
                        self.axis_mapping, self.last_point, point):
                    start_of_row = True
            if start_of_row and self.trigger_enums:
                # Position compare
                # First row, or rows not joined
                # Work out which axis moves most during this point
                axis_name, compare_cts, increasing = _what_moves_most(
                    point, self.axis_mapping)
                # If we have a previous point, how long to be blind for
                # during the turnaround
                if self.last_point is not None:
                    blind = self._how_long_moving_wrong_way(
                        axis_name, point, increasing)
                    half_blind = int(round(blind / TICK / 2))
                    rows.append(seq_row(half_duration=half_blind, dead=1))
                # Create a compare point for the next row
                rows.append(seq_row(
                    trigger=self.trigger_enums[(axis_name, increasing)],
                    position=compare_cts, half_duration=half_frame, live=1))
            elif start_of_row:
                # Row trigger coming in on BITA
                # Produce dead pulse as soon as row has finished
                if self.last_point is not None:
                    rows.append(seq_row(
                        half_duration=MIN_PULSE, dead=1,
                        trigger=Trigger.BITA_0))
                rows.append(seq_row(
                    trigger=Trigger.BITA_1, half_duration=half_frame, live=1))
            elif rows and rows[-1][1] == Trigger.IMMEDIATE and \
                    rows[-1][3] == half_frame and rows[-1][0] < MAX_REPEATS:
                # Repeated time row, just increment the last row repeats
                rows[-1][0] += 1
            else:
                # New time section
                rows.append(seq_row(half_duration=half_frame, live=1))
            if i == self.scan_up_to - 1:
                # Last row, one last dead frame signal
                rows.append(seq_row(half_duration=LAST_PULSE, dead=1))
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
