from operator import itemgetter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from annotypes import Anno, add_call_types
from scanpointgenerator import Point

from malcolm.core import APartName, Attribute, Block, Context, PartRegistrar
from malcolm.modules import builtin, pmac, scanning
from malcolm.modules.pmac.util import all_points_joined
from malcolm.modules.scanning.infos import MinTurnaroundInfo

from ..util import SequencerTable, Trigger

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


def seq_row(
    repeats: int = 1,
    trigger: str = Trigger.IMMEDIATE,
    position: int = 0,
    half_duration: int = MIN_PULSE,
    live: int = 0,
    dead: int = 0,
) -> List:
    """Create a 50% duty cycle pulse with phase1 having given live/dead values"""
    row = [
        repeats,
        trigger,
        position,
        # Phase1
        half_duration,
        live,
        dead,
        0,
        0,
        0,
        0,
        # Phase2
        half_duration,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    return row


def _get_blocks(context: Context, panda_mri: str) -> List[Block]:
    """Get panda, seqA and seqB Blocks using the given context"""
    # {part_name: export_name}
    panda = context.block_view(panda_mri)
    seq_part_names = {}
    for source, export in panda.exports.value.rows():
        if export in SEQ_TABLES:
            assert source.endswith(
                ".table"
            ), "Expected export %s to come from SEQx.table, got %s" % (export, source)
            seq_part_names[source[: -len(".table")]] = export
    assert (
        tuple(sorted(seq_part_names.values())) == SEQ_TABLES
    ), "Expected exported attributes %s, got %s" % (
        SEQ_TABLES,
        panda.exports.value.export,
    )
    # {export_name: mri}
    seq_mris = {}
    for name, mri, _, _, _ in panda.layout.value.rows():
        if name in seq_part_names:
            export = seq_part_names[name]
            seq_mris[export] = mri
    assert sorted(seq_mris) == sorted(
        seq_part_names.values()
    ), "Couldn't find MRI for some of %s" % (seq_part_names.values(),)
    blocks = [panda]
    blocks += [context.block_view(seq_mris[x]) for x in SEQ_TABLES]
    return blocks


def _what_moves_most(
    point: Point, axis_mapping: Dict[str, pmac.infos.MotorInfo]
) -> Tuple[str, int, bool]:
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

    assert diffs, (
        "Can't work out a compare point for %s, maybe none of the axes "
        "connected to the PandA are moving during the scan point?" % point.positions
    )

    # Sort on abs(diff), take the biggest
    axis_name = max(diffs.items(), key=itemgetter(1))[0]
    compare_cts, increasing = compare_increasing[axis_name]
    return axis_name, compare_cts, increasing


def doing_pcomp(row_trigger_value: str) -> bool:
    return row_trigger_value == "Position Compare"


class PandASeqTriggerPart(builtin.parts.ChildPart):
    """Part for operating a pair of SEQ blocks in a PandA to do position
    compare at the start of each row and time based pulses within the row.
    Needs the following exports:

    - seqTableA: table Attribute of the first SEQ block
    - seqTableB: table Attribute of the second SEQ block
    - seqSetEnable: forceSet Method of an SRGATE that is used to gate both SEQs
    """

    def __init__(
        self, name: APartName, mri: AMri, initial_visibility: AInitialVisibility = True
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False
        )
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
        self.axis_mapping: Dict[str, pmac.infos.MotorInfo] = {}
        # The minimum turnaround time for non-joined points
        self.min_turnaround = 0.0
        # The minimum time between turnaround points
        self.min_interval = 0.0
        # {(scannable, increasing): trigger_enum}
        self.trigger_enums: Dict[Tuple[str, bool], str] = {}
        # The panda Block we will be prodding
        self.panda: Optional[Any] = None

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        registrar.hook(
            (
                scanning.hooks.ConfigureHook,
                scanning.hooks.SeekHook,
                scanning.hooks.PostRunArmedHook,
            ),
            self.on_configure,
        )
        registrar.hook(scanning.hooks.RunHook, self.on_run)

    @add_call_types
    def on_report_status(
        self, context: scanning.hooks.AContext
    ) -> scanning.hooks.UInfos:
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

    def setup_pcomp_dicts(
        self, seqa: Block, seqb: Block, axis_mapping: Dict[str, pmac.infos.MotorInfo]
    ) -> None:
        """Setup the axis_mapping and trigger_enum dicts for position compare"""
        # Check that both sequencers are pointing to the same encoders
        seq_pos = {}
        for suff in "abc":
            # Something like INENC1.VAL or ZERO
            seqa_pos_inp = seqa["pos" + suff].value
            seqb_pos_inp = seqb["pos" + suff].value
            assert (
                seqa_pos_inp == seqb_pos_inp
            ), "SeqA Pos%s = %s != SeqB Pos%s = %s" % (
                suff,
                seqa_pos_inp,
                suff,
                seqb_pos_inp,
            )
            seq_pos[seqa_pos_inp] = "POS%s" % suff.upper()

        # Fix the mres and offsets from the panda positions table
        assert self.panda, "No PandA"
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
                    self.trigger_enums[(scannable, True)] = "%s>=POSITION" % pos
                    self.trigger_enums[(scannable, False)] = "%s<=POSITION" % pos
        # Check we have at least one entry
        assert self.axis_mapping, (
            "None of the seq inputs %s can be mapped to scannable names "
            "in %s. Did you define datasetName entries for these rows in "
            "the PandA positions table?" % (sorted(seq_pos), sorted(axis_mapping))
        )

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
    ) -> None:
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
        infos: List[MinTurnaroundInfo] = MinTurnaroundInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(
                infos
            )
            self.min_turnaround = max(pmac.util.MIN_TIME, infos[0].gap)
            self.min_interval = infos[0].interval
        else:
            self.min_turnaround = pmac.util.MIN_TIME
            self.min_interval = pmac.util.MIN_INTERVAL

        # Get panda Block, and the sequencer Blocks so we can do some checking
        self.panda, seqa, seqb = _get_blocks(context, panda_mri)

        # Fill in motor infos and trigger lookups
        motion_axes = pmac.util.get_motion_axes(generator, axesToMove)
        self.axis_mapping = {}
        self.trigger_enums = {}

        if motion_axes:
            # Need to fill in the axis mapping
            axis_mapping = pmac.util.cs_axis_mapping(
                context, context.block_view(pmac_mri).layout.value, motion_axes
            )
            if doing_pcomp(row_trigger):
                # We need to do position compare, so only place the infos into
                # axis_mapping that our sequencer can see
                self.setup_pcomp_dicts(seqa, seqb, axis_mapping)
            else:
                # We rely on the inputs coming into SEQ bitA
                assert (
                    seqa["bita"].value == seqb["bita"].value != "ZERO"
                ), "SEQ.bita inputs need to point to the same non-zero input"
                self.axis_mapping = axis_mapping

        # TODO:
        # Check that the sequencer blocks have the correct wiring, delays, and
        # setup monitors on the active field
        assert seqa
        assert seqb

        # load up the first SEQ
        self._fill_sequencer(self.panda[SEQ_TABLES[0]])

    def _how_long_moving_wrong_way(
        self, axis_name: str, point: Point, increasing: bool
    ) -> float:
        """Work out the turnaround for the axis with the given MotorInfo, and
        how long it is moving in the opposite direction from where we want it to
        be going for point"""
        min_turnaround = max(self.min_turnaround, point.delay_after)
        time_arrays, velocity_arrays = pmac.util.profile_between_points(
            self.axis_mapping, self.last_point, point, min_turnaround, self.min_interval
        )
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
                assert i < len(velocity_array) - 1, (
                    "Last point of %s is wrong direction" % velocity_array
                )
                break
        blind = time_array[i]
        return blind

    @staticmethod
    def _get_row_indices(points) -> Tuple[np.array, np.array]:
        """Generate list of start and end indices for separate rows

        This excludes the initial row, which is handled separately.
        """
        points_joined = all_points_joined(points)

        if points_joined is not None and len(points_joined) > 0:
            results = np.nonzero(np.invert(points_joined))[0]
            results += 1
            start_indices = results
        else:
            start_indices = np.array([])

        # end_index = start_index + size
        end_indices = np.empty(len(start_indices), dtype=int)
        if start_indices.size:
            end_indices[:-1] = start_indices[1:]
            end_indices[-1] = len(points)

        return start_indices, end_indices

    @staticmethod
    def _generate_immediate_rows(durations):
        """Create a series of immediate rows from `durations`"""
        if len(durations) == 0:
            return []

        pairwise_equal = np.empty(len(durations), dtype=bool)
        pairwise_equal[0] = True  # Initial duration starts first row

        np.not_equal(durations[:-1], durations[1:], out=pairwise_equal[1:])
        start_indices = np.nonzero(pairwise_equal)
        seq_durations = durations[start_indices]
        seq_lengths = np.diff(np.append(start_indices, len(durations)))

        rows = []
        for duration, count in zip(seq_durations, seq_lengths):
            half_frame = int(round(duration / TICK / 2))
            complete_rows = count // MAX_REPEATS
            remaining = count % MAX_REPEATS

            rows = [
                seq_row(repeats=MAX_REPEATS, half_duration=half_frame, live=1)
            ] * complete_rows
            rows.append(seq_row(repeats=remaining, half_duration=half_frame, live=1))

        return rows

    def _generate_triggered_rows(self, points, start_index, end_index, add_blind):
        """Generate sequencer rows corresponding to a triggered points row"""
        rows = []
        initial_point = points[start_index]
        half_frame = int(round(initial_point.duration / TICK / 2))

        if self.trigger_enums:
            # Position compare
            # First row, or rows not joined
            # Work out which axis moves most during this point
            axis_name, compare_cts, increasing = _what_moves_most(
                initial_point, self.axis_mapping
            )

            if add_blind:
                # How long to be blind for during the turnaround
                blind = self._how_long_moving_wrong_way(
                    axis_name, initial_point, increasing
                )
                half_blind = int(round(blind / TICK / 2))
                rows.append(seq_row(half_duration=half_blind, dead=1))

            # Create a compare point for the next row
            rows.append(
                seq_row(
                    trigger=self.trigger_enums[(axis_name, increasing)],
                    position=compare_cts,
                    half_duration=half_frame,
                    live=1,
                )
            )
        else:
            # Row trigger coming in on BITA

            if add_blind:
                # Produce dead pulse as soon as row has finished
                rows.append(
                    seq_row(half_duration=MIN_PULSE, dead=1, trigger=Trigger.BITA_0)
                )

            rows.append(
                seq_row(trigger=Trigger.BITA_1, half_duration=half_frame, live=1)
            )

        rows.extend(
            self._generate_immediate_rows(points.duration[start_index + 1 : end_index])
        )

        return rows

    def _fill_sequencer(self, seq_table: Attribute) -> None:
        assert self.generator, "No generator"
        points = self.generator.get_points(self.loaded_up_to, self.scan_up_to)

        if points is None or len(points) == 0:
            table = SequencerTable.from_rows([])
            seq_table.put_value(table)
            return

        rows = []

        if not self.axis_mapping:
            # No position compare or row triggering required
            rows.extend(self._generate_immediate_rows(points.duration))

            # one last dead frame signal
            rows.append(seq_row(half_duration=LAST_PULSE, dead=1))

            if len(rows) > SEQ_TABLE_ROWS:
                raise Exception(
                    "Seq table: {} rows with {} maximum".format(
                        len(rows), SEQ_TABLE_ROWS
                    )
                )

            table = SequencerTable.from_rows(rows)
            seq_table.put_value(table)
            return

        start_indices, end_indices = self._get_row_indices(points)

        point = points[0]
        first_point_static = point.positions == point.lower == point.upper
        end = start_indices[0] if start_indices.size else len(points)
        if not first_point_static:
            # If the motors are moving during this point then
            # wait for triggers
            rows.extend(self._generate_triggered_rows(points, 0, end, False))
        else:
            # This first row should not wait, and will trigger immediately
            rows.extend(self._generate_immediate_rows(points.duration[0:end]))

        for start, end in zip(start_indices, end_indices):
            # First row handled outside of loop
            self.last_point = points[start - 1]

            rows.extend(self._generate_triggered_rows(points, start, end, True))

        # one last dead frame signal
        rows.append(seq_row(half_duration=LAST_PULSE, dead=1))

        if len(rows) > SEQ_TABLE_ROWS:
            raise Exception(
                "Seq table: {} rows with {} maximum".format(len(rows), SEQ_TABLE_ROWS)
            )

        table = SequencerTable.from_rows(rows)
        seq_table.put_value(table)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # Call sequence table enable
        assert self.panda, "No PandA"
        self.panda.seqSetEnable()
