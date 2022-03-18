from operator import itemgetter
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator, Point, Points

from malcolm.core import APartName, Block, Context, PartRegistrar
from malcolm.modules import builtin, pmac, scanning
from malcolm.modules.pmac.util import MinTurnaround, get_min_turnaround

from ..doublebuffer import MIN_PULSE, TICK, DoubleBuffer, SequencerRows
from ..util import Trigger

# The SEQ.table attributes that should be present in PANDA.exports
SEQ_TABLES = ("seqTableA", "seqTableB")

with Anno("Scannable name for sequencer input"):
    APos = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

# SeqTriggers processing batch size
BATCH_SIZE: int = 5000


class SeqTriggers:
    """A class that generates Sequencer (SEQ) block triggers from a Points generator."""

    def __init__(
        self,
        generator: CompoundGenerator,
        axis_mapping: Dict[str, pmac.infos.MotorInfo],
        trigger_enums: Dict[Tuple[str, bool], str],
        min_turnaround: float,
    ) -> None:
        self.generator: CompoundGenerator = generator
        self.axis_mapping: Dict[str, pmac.infos.MotorInfo] = axis_mapping
        self.trigger_enums: Dict[Tuple[str, bool], str] = trigger_enums
        self.min_turnaround: float = min_turnaround
        self.last_point: Point = None

    @staticmethod
    def _what_moves_most(
        point: Point, axis_mapping: Dict[str, pmac.infos.MotorInfo]
    ) -> Tuple[str, int, bool]:
        """Return the axis from `axis_mapping` that moves most for this point."""
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

    def _how_long_moving_wrong_way(
        self, axis_name: str, point: Point, increasing: bool
    ) -> float:
        """Return the duration that the given axis is moving in the opposite direction from
        that required for `point`, during the prior turnaround."""
        assert self.min_turnaround, f"{self.name}: no MinTurnaround assigned"
        min_turnaround = max(self.min_turnaround.time, point.delay_after)
        time_arrays, velocity_arrays = pmac.util.profile_between_points(
            self.axis_mapping,
            self.last_point,
            point,
            min_turnaround,
            self.min_turnaround.interval,
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
    def _get_row_indices(points: Points) -> Tuple[np.ndarray, np.ndarray]:
        """Generate list of start and end indices for separate rows.

        The first point (index 0) is not registered as a separate row. This is because
        for the first row of a scan the triggering is handled separately, and for later
        batches of points the initial value is from a previous row.
        """
        points_joined = pmac.util.all_points_joined(points)

        if points_joined is not None and len(points_joined) > 0:
            start_indices = np.nonzero(np.invert(points_joined))[0]
            start_indices += 1
        else:
            start_indices = np.array([])

        # end_index = start_index + size
        end_indices = np.empty(len(start_indices), dtype=int)
        if start_indices.size:
            end_indices[:-1] = start_indices[1:]
            end_indices[-1] = len(points)

        return start_indices, end_indices

    @staticmethod
    def _create_immediate_rows(durations: Sequence[float]) -> SequencerRows:
        """Generate sequencer rows with 'Immediate' trigger type, from `durations`."""
        if len(durations) == 0:
            return SequencerRows()

        pairwise_equal = np.empty(len(durations), dtype=bool)
        pairwise_equal[0] = True  # Initial duration starts first row

        np.not_equal(durations[:-1], durations[1:], out=pairwise_equal[1:])
        start_indices = np.nonzero(pairwise_equal)
        seq_durations = durations[start_indices]
        seq_lengths = np.diff(np.append(start_indices, len(durations)))

        rows = SequencerRows()
        for duration, count in zip(seq_durations, seq_lengths):
            half_frame = int(round(duration / TICK / 2))
            rows.add_seq_entry(count, half_duration=half_frame, live=1)

        return rows

    def _create_triggered_rows(
        self, points: Points, start_index: int, end_index: int, add_blind: bool
    ) -> SequencerRows:
        """Generate sequencer rows corresponding to a triggered points row."""
        initial_point: Point = points[start_index]
        half_frame: int = int(round(initial_point.duration / TICK / 2))

        rows = SequencerRows()
        if self.trigger_enums:
            # Position compare
            # First row, or rows not joined
            # Work out which axis moves most during this point
            axis_name, compare_cts, increasing = self._what_moves_most(
                initial_point, self.axis_mapping
            )

            if add_blind:
                # How long to be blind for during the turnaround
                blind = self._how_long_moving_wrong_way(
                    axis_name, initial_point, increasing
                )
                half_blind = int(round(blind / TICK / 2))
                rows.add_seq_entry(half_duration=half_blind, dead=1)

            # Create a compare point for the next row
            rows.add_seq_entry(
                trigger=self.trigger_enums[(axis_name, increasing)],
                position=compare_cts,
                half_duration=half_frame,
                live=1,
            )
        else:
            # Row trigger coming in on BITA

            if add_blind:
                # Produce dead pulse as soon as row has finished
                rows.add_seq_entry(
                    half_duration=MIN_PULSE, dead=1, trigger=Trigger.BITA_0
                )

            rows.add_seq_entry(trigger=Trigger.BITA_1, half_duration=half_frame, live=1)

        rows.extend(
            self._create_immediate_rows(points.duration[start_index + 1 : end_index])
        )

        return rows

    @staticmethod
    def _overlapping_points_range(generator, start: int, end: int) -> Iterator[Points]:
        """Yield a series of `Points` objects that cover the given range.

        Yielded points overlap by one point to indicate whether the start of a given
        batch corresponds to the middle of a row.
        """
        if start == end:
            return

        low_index = start
        high_index = min(start + BATCH_SIZE, end)
        while True:
            yield generator.get_points(low_index, high_index)

            if high_index == end:
                break

            low_index = high_index - 1  # Include final point from previous range
            high_index = min(low_index + BATCH_SIZE + 1, end)

    def get_rows(self, loaded_up_to: int, scan_up_to: int) -> Iterator[SequencerRows]:
        """Yield a series of `SequencerRows` that correspond to the given range."""
        for points in self._overlapping_points_range(
            self.generator, loaded_up_to, scan_up_to
        ):

            if not self.axis_mapping:
                # No position compare or row triggering required
                durations = points.duration[1:] if self.last_point else points.duration
                yield self._create_immediate_rows(durations)
                self.last_point = points[-1]
            else:
                start_indices, end_indices = self._get_row_indices(points)

                # Handle the first scan row from the current batch of points
                end = start_indices[0] if start_indices.size else len(points)
                if self.last_point is None:
                    # This is the beginning of the scan
                    yield self._create_triggered_rows(points, 0, end, False)
                    self.last_point = points[end - 1]
                else:
                    # This is the beginning of subsequent batches.
                    # Sequence table rows are only added here if the previous batch
                    # of points finished in the middle of a continuous scan row.
                    # The first point of the current batch is from the previous batch.
                    yield self._create_immediate_rows(points.duration[1:end])

                # Remaining scan rows from the current batch of points.
                for start_i, end_i in zip(start_indices, end_indices):
                    yield self._create_triggered_rows(points, start_i, end_i, True)
                    self.last_point = points[end_i - 1]

        rows = SequencerRows()
        # add one last dead frame signal
        rows.add_seq_entry(half_duration=MIN_PULSE, dead=1)
        # add continuous loop to prevent sequencer switch
        rows.add_seq_entry(count=0)
        yield rows

        self.last_point = None


def _get_blocks(context: Context, panda_mri: str) -> List[Block]:
    """Get panda, seqA, and seqB Blocks using the given context."""
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


def doing_pcomp(row_trigger_value: str) -> bool:
    """Indicate whether the row_trigger is for position compare."""
    return row_trigger_value == "Position Compare"


class PandASeqTriggerPart(builtin.parts.ChildPart):
    """Part for operating a pair of Sequencer (SEQ) blocks in a PandA to do position
    compare at the start of each row, and time based pulses within the row.

    Needs the following exports:

    - seqTableA: table Attribute of the first SEQ block
    - seqTableB: table Attribute of the second SEQ block
    - seqSetEnable: forceSet Method of an SRGATE that is used to gate both SEQs
    - seqReset: forceRst Method of an SRGATE that is used to gate both SEQs
    """

    def __init__(
        self, name: APartName, mri: AMri, initial_visibility: AInitialVisibility = True
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False
        )
        # Stored generator for positions
        self.generator: scanning.hooks.AGenerator = None
        # The last index we have loaded
        self.loaded_up_to: int = 0
        # The last scan point index of the current run
        self.scan_up_to: int = 0
        # If we are currently loading then block loading more points
        self.loading: bool = False
        # What is the mapping of scannable name to MotorInfo
        self.axis_mapping: Dict[str, pmac.infos.MotorInfo] = {}
        # The minimum turnaround time for non-joined points
        self.min_turnaround: Optional[MinTurnaround] = None
        # {(scannable, increasing): trigger_enum}
        self.trigger_enums: Dict[Tuple[str, bool], str] = {}
        # The panda Block we will be prodding
        self.panda: Optional[Any] = None
        # The DoubleBuffer object used to load tables during a scan
        self.db_seq_table: Optional[DoubleBuffer] = None

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        registrar.hook(
            (
                scanning.hooks.ConfigureHook,
                scanning.hooks.SeekHook,
            ),
            self.on_configure,
        )
        registrar.hook(scanning.hooks.PreRunHook, self.on_pre_run)
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(builtin.hooks.ResetHook, self.on_reset)
        registrar.hook(
            (scanning.hooks.AbortHook, scanning.hooks.PauseHook), self.on_abort
        )
        registrar.hook(scanning.hooks.PostRunArmedHook, self.post_inner_scan)

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
        """Setup the axis mapping and trigger enum attributes for position compare."""
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

    def reset_seq(self, context):
        """Reset the PandA sequencer using the given context.

        We need to use the correct context when calling this function, as it will
        otherwise get blocked.
        """
        panda = context.block_view(self.panda_mri)
        panda.seqReset()

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
        context.unsubscribe_all()

        self.generator = generator
        self.loaded_up_to = completed_steps
        self.scan_up_to = completed_steps + steps_to_do
        self.loading = False

        # Get the panda and the pmac we will be using
        child = context.block_view(self.mri)
        self.panda_mri = child.panda.value  # Retain for use during reset / abort

        pmac_mri = child.pmac.value
        row_trigger = child.rowTrigger.value

        # See if there is a minimum turnaround
        self.min_turnaround = get_min_turnaround(part_info)

        # Get panda Block, and the sequencer Blocks so we can do some checking
        self.panda, seqa, seqb = _get_blocks(context, self.panda_mri)

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

        seq_triggers = SeqTriggers(
            self.generator,
            self.axis_mapping,
            self.trigger_enums,
            self.min_turnaround,
        )

        rows_gen = seq_triggers.get_rows(self.loaded_up_to, self.scan_up_to)

        self.db_seq_table = DoubleBuffer(context, seqa, seqb)

        assert self.db_seq_table, "No DoubleBuffer"
        self.db_seq_table.configure(rows_gen)

    @add_call_types
    def on_pre_run(self, context: scanning.hooks.AContext) -> None:
        assert self.panda, "No PandA"
        assert self.db_seq_table, "No DoubleBuffer"
        # If there are MotorInfo's enable seqTableA here so ready to receive the
        # first signal (once the motors have moved to the first point).
        if self.axis_mapping:
            self.panda.seqSetEnable()

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # When there are no MotorInfo's the first row will have Trigger.IMMEDIATE
        # so don't enable seqTableA until running.
        if not self.axis_mapping:
            self.panda.seqSetEnable()
        futures = self.db_seq_table.run()
        context.wait_all_futures(futures)

    @add_call_types
    def on_reset(self, context: builtin.hooks.AContext) -> None:
        super().on_reset(context)
        self.on_abort(context)

    @add_call_types
    def on_abort(self, context: builtin.hooks.AContext) -> None:
        try:
            self.reset_seq(context)
        except (AttributeError, KeyError):
            # Ensure we can reset or abort if different design is used for PandA
            pass

        if self.db_seq_table is not None:
            self.db_seq_table.clean_up()

    @add_call_types
    def post_inner_scan(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
    ) -> None:
        self.on_abort(context)
        self.on_configure(
            context, completed_steps, steps_to_do, part_info, generator, axesToMove
        )
