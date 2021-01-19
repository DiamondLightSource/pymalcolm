# Treat all division as float division even in python2
from __future__ import division

from annotypes import TYPE_CHECKING

from .util import SequencerTable, Trigger

if TYPE_CHECKING:
    from typing import List

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
MIN_TABLE_DURATION = 15.0


class SequencerRows:
    def __init__(self, rows=None):
        if rows:
            self._rows = rows
            self._duration = self._calculate_duration(self._rows)
        else:
            self._rows = []
            self._duration = 0

    def add_seq_entry(
        self,
        count=1,
        trigger=Trigger.IMMEDIATE,
        position=0,
        half_duration=MIN_PULSE,
        live=0,
        dead=0,
        trim=0,
    ):
        complete_rows = count // MAX_REPEATS
        remaining = count % MAX_REPEATS

        row = self._seq_row(
            MAX_REPEATS, trigger, position, half_duration, live, dead, trim
        )
        self._rows.extend([row] * complete_rows)
        self._rows.append(
            self._seq_row(remaining, trigger, position, half_duration, live, dead, trim)
        )
        self._duration += count * (2 * half_duration - trim)

    def split(self, count):
        """Separate this object into two SequencerRows objects, deducting the
        time delay required to switch between sequencers from the end of the
        current object, and returning the remainder."""

        assert len(self._rows) > 0, "Zero length seq rows should never be split"

        if len(self._rows) >= count:
            final_row = self._rows[count - 1]
            if final_row[0] == 0:  # Row in continuous loop
                assert len(self._rows) == count  # Continuous loop always at end
                return SequencerRows()

            if final_row[0] == 1:
                remainder = SequencerRows(self._rows[count:])
                self._rows = self._rows[:count]

            elif final_row[0] > 1:
                final_row = list(final_row)
                final_row[0] -= 1
                remainder = SequencerRows([tuple(final_row)])
                remainder.extend(SequencerRows(self._rows[count:]))
                final_row[0] = 1
                self._rows = self._rows[: count - 1]
                self._rows.append(tuple(final_row))
        else:
            remainder = SequencerRows()

            if self._rows[-1][0] == 0:
                return remainder

            if self._rows[-1][0] > 1:
                final_row = list(self._rows[-1])
                final_row[0] -= 1
                self._rows[-1] = tuple(final_row)
                final_row[0] = 1
                self._rows += [final_row]

        final_self_row = list(self._rows[-1])
        final_self_row[10] -= SEQ_TABLE_SWITCH_DELAY
        self._rows[-1] = tuple(final_self_row)
        self._duration -= SEQ_TABLE_SWITCH_DELAY
        self._duration -= remainder.duration
        return remainder

    def extend(self, other):
        self._rows += other._rows
        self._duration += other._duration

    def get_table(self):
        return SequencerTable.from_rows(self._rows)

    def as_tuple(self):
        """Used for comparisons during testing."""
        return tuple(self._rows)

    @property
    def duration(self):
        return self._duration * TICK

    def __len__(self):
        return len(self._rows)

    @staticmethod
    def _seq_row(
        repeats: int = 1,
        trigger: str = Trigger.IMMEDIATE,
        position: int = 0,
        half_duration: int = MIN_PULSE,
        live: int = 0,
        dead: int = 0,
        trim: int = 0,
    ) -> List:
        """Create a pulse with phase1 having given live/dead values

        If trim=0, there is a 50% duty cycle. Trim reduces the total duration
        """
        return (
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
            half_duration - trim,
            0,
            0,
            0,
            0,
            0,
            0,
        )

    @staticmethod
    def _calculate_duration(rows):
        duration = 0.0
        for row in rows:
            duration += row[0] * (row[3] + row[10])

        return duration


class DoubleBuffer:
    def __init__(self, context, seq_a, seq_b):
        self._context = context
        self._table_map = {"seqA": seq_a, "seqB": seq_b}
        self._seq_status = None
        self._futures = []
        self._finished = True
        self._table_gen = None

    def _fill_table(self, table, gen):
        seq_table = self._table_map[table]
        seq_table.table.put_value(next(gen))

    @staticmethod
    def _get_tables(rows_gen):
        rows = SequencerRows()
        for rs in rows_gen:
            rows.extend(rs)

            if rows.duration > MIN_TABLE_DURATION or len(rows) > SEQ_TABLE_ROWS:
                while True:
                    remainder = rows.split(SEQ_TABLE_ROWS)
                    yield rows.get_table()
                    rows = remainder

                    if len(rows) <= SEQ_TABLE_ROWS:
                        break
        if len(rows):
            yield rows.get_table()

    def configure(self, rows_generator):
        self._clean_up()
        self._table_gen = self._get_tables(rows_generator)

        try:
            self._fill_table("seqA", self._table_gen)
            self._fill_table("seqB", self._table_gen)
        except StopIteration:
            self._finished = True
        else:
            self._finished = False

    def _seq_active_handler(self, value, table="seqA"):
        prev = self._seq_status[table]
        if prev is not None and prev and not value:
            # We only care when the seq is deactivated
            try:
                self._fill_table(table, self._table_gen)
            except StopIteration:
                self._clean_up()
                return

        self._seq_status[table] = value

    def _setup_subscriptions(self):
        for table in self._table_map:
            self._futures += [
                self._table_map[table].active.subscribe_value(
                    self._seq_active_handler, table
                )
            ]

    def run(self):
        if not self._finished:
            self._setup_subscriptions()

        return self._futures

    def _remove_subscriptions(self):
        for future in self._futures:
            self._context.unsubscribe(future)

        self._futures = []

    def _clean_up(self):
        self._remove_subscriptions()
        self._seq_status = {"seqA": None, "seqB": None}
        self._finished = True

    def abort(self):
        self._clean_up()
