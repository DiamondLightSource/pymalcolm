# Treat all division as float division even in python2
from __future__ import division

from annotypes import TYPE_CHECKING
from scanpointgenerator import Point

from malcolm.modules import pmac
from .util import SequencerTable, Trigger

import numpy as np

if TYPE_CHECKING:
    from typing import List, Tuple, Dict

#: The number of sequencer table rows
SEQ_TABLE_ROWS = 4096

# How long is a single tick if prescaler is 0
TICK = 8e-9

# How long is the smallest pulse that will travel across TTL
MIN_PULSE = 1250  # ticks = 10us

# Maximum repeats of a single row
MAX_REPEATS = 4096

# How long the last pulse should be (50% duty cycle) to make sure we don't flip
# to an unfilled sequencer and produce a false pulse. This should be at least
# as long as it takes the PandA EPICS driver to see that we got the last frame
# and disarm PCAP
LAST_PULSE = 125000000  # ticks = 1s

# The number of clock ticks required to switch between the two sequencers
SEQ_TABLE_SWITCH_DELAY = 6

# Default minimum table duration. This is the minimum time (in seconds) for a
# table used by the double-buffering system.
MIN_TABLE_DURATION = 30000.0

# Processing batch size
BATCH_SIZE = 5000


class SequencerRows:
    def __init__(self, rows=None):
        if rows:
            self._rows = rows
            self._duration = self._calculate_duration(self._rows)
        else:
            self._rows = []
            self._duration = 0

    def add_seq_entry(self, count=1, trigger=Trigger.IMMEDIATE, position=0,
                      half_duration=MIN_PULSE, live=0, dead=0, trim=0):
        complete_rows = count // MAX_REPEATS
        remaining = count % MAX_REPEATS

        row = self._seq_row(MAX_REPEATS, trigger, position, half_duration, live,
                            dead, trim)
        self._rows.extend(row * complete_rows)
        self._rows.append(self._seq_row(remaining, trigger, position,
                                        half_duration, live, dead, trim))
        self._duration += count * (2 * half_duration - trim)

    def split(self, count):
        """Separate this object into two SequencerRows objects, deducting the
        time delay required to switch between sequencers from the end of the
        current object, and returning the remainder."""

        assert len(self._rows) > 0, "Zero length seq rows should never be split"

        if len(self._rows) >= count:
            final_row = self._rows[count-1]
            if final_row[0] == 0:  # Row in continuous loop
                assert len(self._rows) == count
                return SequencerRows()

            if final_row[0] == 1:
                remainder = SequencerRows(self._rows[count:])
                self._rows = self._rows[:count]

            elif final_row[0] > 1:
                initial_remainder = final_row[:]
                initial_remainder[0] -= 1
                remainder = SequencerRows([initial_remainder])
                remainder.extend(SequencerRows(self._rows[count:]))
                self._rows = self._rows[:count]
                self._rows[-1][0] = 1
        else:
            remainder = SequencerRows()

            if self._rows[-1][0] == 0:
                return remainder

            if self._rows[-1][0] > 1:
                final_row = self._rows[-1][:]
                self._rows[-1][0] -= 1
                final_row[0] = 1
                self._rows += [final_row]

        self._rows[-1][10] -= SEQ_TABLE_SWITCH_DELAY
        self._duration -= SEQ_TABLE_SWITCH_DELAY
        self.duration -= remainder.duration
        return remainder

    def extend(self, other):
        self._rows += other._rows
        self._duration += other._duration

    def get_table(self):
        return SequencerTable.from_rows(self._rows)

    @property
    def duration(self):
        return self._duration * TICK

    def __len__(self):
        return len(self._rows)

    @staticmethod
    def _seq_row(repeats=1, trigger=Trigger.IMMEDIATE, position=0,
                 half_duration=MIN_PULSE, live=0, dead=0, trim=0):
        # type: (int, str, int, int, int, int, int) -> List
        """Create a pulse with phase1 having given live/dead values

        If trim=0, there is a 50% duty cycle. Trim reduces the total duration
        """
        return [repeats, trigger, position,
                # Phase1
                half_duration, live, dead, 0, 0, 0, 0,
                # Phase2
                half_duration - trim, 0, 0, 0, 0, 0, 0]

    @staticmethod
    def _calculate_duration(rows):
        duration = 0.0
        for row in rows:
            duration += row[0] * (row[3] + row[10])

        return duration


class SeqTriggers(object):
    """Class that provides Sequencer triggers for input Points generator"""

    def __init__(self, generator, axis_mapping, trigger_enums, min_turnaround,
                 min_interval):
        self.generator = generator
        self.axis_mapping = axis_mapping
        self.trigger_enums = trigger_enums
        self.min_turnaround = min_turnaround
        self.min_interval = min_interval
        self.last_point = None

    @staticmethod
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

    def _how_long_moving_wrong_way(self, axis_name, point, increasing):
        # type: (str, Point, bool) -> float
        """Work out the turnaround for the axis with the given MotorInfo, and
        how long it is moving in the opposite direction from where we want it to
        be going for point"""
        min_turnaround = max(self.min_turnaround, point.delay_after)
        time_arrays, velocity_arrays = pmac.util.profile_between_points(
            self.axis_mapping, self.last_point, point, min_turnaround,
            self.min_interval)
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

    @staticmethod
    def _get_row_indices(points):
        """Generate list of start and end indices for separate rows

        The first point (index 0) is not registered as a separate row. This is
        because for the first row of a scan, the triggering is handled
        separately, and for later batches of points, the initial value is from
        a previous row.
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
    def _create_immediate_rows(durations):
        """Create a series of immediate rows from `durations`"""
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

    def _create_triggered_rows(self, points, start_index, end_index,
                               add_blind):
        """Generate sequencer rows corresponding to a triggered points row"""
        rows = []
        initial_point = points[start_index]
        half_frame = int(round(initial_point.duration / TICK / 2))

        rows = SequencerRows()
        if self.trigger_enums:
            # Position compare
            # First row, or rows not joined
            # Work out which axis moves most during this point
            axis_name, compare_cts, increasing = self._what_moves_most(
                initial_point, self.axis_mapping)

            if add_blind:
                # How long to be blind for during the turnaround
                blind = self._how_long_moving_wrong_way(
                    axis_name, initial_point, increasing)
                half_blind = int(round(blind / TICK / 2))
                rows.add_seq_entry(half_duration=half_blind, dead=1)

            # Create a compare point for the next row
            rows.add_seq_entry(
                trigger=self.trigger_enums[(axis_name, increasing)],
                position=compare_cts, half_duration=half_frame, live=1)
        else:
            # Row trigger coming in on BITA

            if add_blind:
                # Produce dead pulse as soon as row has finished
                rows.add_seq_entry(
                    half_duration=MIN_PULSE, dead=1, trigger=Trigger.BITA_0)

            rows.add_seq_entry(trigger=Trigger.BITA_1,
                               half_duration=half_frame, live=1)

        rows.extend(self._create_immediate_rows(
            points.duration[start_index + 1: end_index]))

        return rows

    @staticmethod
    def _overlapping_points_range(generator, start, end):
        """Create a series of points objects that cover the entire range.

        Yielded points overlap by one point to identify whether the start of a
        given batch corresponds to the middle of a row.
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

    def get_rows(self, loaded_up_to, scan_up_to):
        for points in self._overlapping_points_range(self.generator,
                                                     loaded_up_to, scan_up_to):

            if not self.axis_mapping:
                # No position compare or row triggering required
                durations = points.duration[1:] if self.last_point \
                    else points.duration
                yield self._create_immediate_rows(durations)
                self.last_point = points[-1]
            else:
                start_indices, end_indices = self._get_row_indices(points)

                # Handle first row of batch
                end = start_indices[0] if start_indices.size else len(points)
                if self.last_point is None:
                    # This is the beginning of the scan
                    point = points[0]
                    first_point_static = point.positions == point.lower == \
                        point.upper

                    if not first_point_static:
                        # If the motors are moving during this point then
                        # wait for triggers
                        yield self._create_triggered_rows(points, 0, end, False)
                    else:
                        # This first row will trigger immediately
                        yield self._create_immediate_rows(points.duration[0:end])

                    self.last_point = points[end - 1]
                else:  # This is the beginning of the batch
                    # The first point is from the previous batch
                    yield self._create_immediate_rows(points.duration[1:end])

                for start_i, end_i in zip(start_indices, end_indices):
                    # First row handled outside of loop
                    yield self._create_triggered_rows(points, start_i, end_i,
                                                      True)
                    self.last_point = points[end_i - 1]

        rows = SequencerRows()
        # add one last dead frame signal
        rows.add_seq_entry(half_duration=LAST_PULSE, dead=1)
        # add continuous loop to prevent sequencer switch
        rows.add_seq_entry(count=0)
        yield rows

        self.last_point = None


class DoubleBufferSeqTable:
    def __init__(self, seq_a, seq_b):
        self._seq_a = seq_a
        self._seq_b = seq_b
        # self.current_table = None
        self._table_map = {"seqA": self._seq_a, "seqB": self._seq_b}

        # self._processing = False

    # def update(self, finished_table, generator, req_duration):
    #     start = datetime.now()

    #     required_duration = max(req_duration, MINIMUM_DURATION)

    #     if self._processing:
    #         raise Exception("Seq table update called during previous table"
    #                         "processing")
    #     self._processing = True

    #     if finished_table is not None and finished_table != self.current_table:
    #         raise Exception("Seq tables out of sync with loading routine.")

    #     if self.current_table is None or finished_table == "seqB":
    #         next_table = "seqA"
    #     else:
    #         next_table = "seqB"

    #     additional_duration = required_duration - self._rows.duration
    #     self._rows.extend(generator.getRows(additional_duration))

    #     extra_rows = self._rows.reduce_to_fit(SEQ_TABLE_ROWS)
    #     if self._rows.duration < required_duration and len(extra_rows) > 0:
    #         raise Exception("Filled seq table does not meet minimum duration")

    #     self._fill_table(next_table, self._rows)
    #     self._rows = extra_rows

    #     time_elapsed = (datetime.now() - start).total_seconds()
    #     if time_elapsed > required_duration:
    #         raise Exception("SeqTable processing is longer than min duration,"
    #                         "at %s seconds\nMin duration: %s"
    #                         % (time_elapsed, required_duration))

    #     self._processing = False

    #     #TODO:

    def _fill_table(self, table, value):
        seq_table = self._table_map[table]
        seq_table.put_value(value)

    @staticmethod
    def _get_tables(rows_gen, minimum_duration=MIN_TABLE_DURATION):
        rows = SequencerRows()
        for rs in rows_gen:
            rows.extend(rs)

            if rows.duration > minimum_duration or len(rows) > SEQ_TABLE_ROWS:
                while True:
                    remainder = rows.split(SEQ_TABLE_ROWS)
                    yield rows.get_table()
                    rows = remainder

                    if len(rows) <= SEQ_TABLE_ROWS:
                        break

        yield rows.get_table()

    def configure(self, rows_gen):
        tables = list(self._get_tables(rows_gen))

        if len(tables) > 1:
            raise Exception("Seq table: Too many rows")

        self._fill_table("seqA", tables[0])

    def run(self):
        pass
