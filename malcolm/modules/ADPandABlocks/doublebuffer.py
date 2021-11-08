from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, TypeVar

from malcolm.core import Block, Context, Future

from .util import SequencerRow, SequencerTable, Trigger

#: The number of sequencer table rows
SEQ_TABLE_ROWS: int = 4096

# How long is a single tick if prescaler is 0
TICK: float = 8e-9

# How long is the smallest pulse that will travel across TTL
MIN_PULSE: int = 1250  # ticks = 10us

# Maximum repeats of a single row
MAX_REPEATS: int = 4096

# The number of clock ticks required to switch between the two sequencers
SEQ_TABLE_SWITCH_DELAY: int = 6

# Default minimum table duration. This is the minimum time (in seconds) for a
# table used by the double buffering system.
MIN_TABLE_DURATION: float = 15.0

T = TypeVar("T", bound="SequencerRows")  # Allows us to return cls from classmethod


class SequencerRows:
    """A class that represents a series of rows for the Sequencer (SEQ) block."""

    def __init__(self, rows: List[SequencerRow] = None) -> None:
        self._rows: List[SequencerRow] = []
        self._duration: float = 0

        if rows:
            self._rows = rows
            self._duration = self._calculate_duration(self._rows)

    @classmethod
    def from_tuple_list(cls: Type[T], rows: List[Tuple]) -> T:
        return cls([SequencerRow(*row) for row in rows])

    def add_seq_entry(
        self,
        count=1,
        trigger=Trigger.IMMEDIATE,
        position=0,
        half_duration=MIN_PULSE,
        live=0,
        dead=0,
        trim=0,
    ) -> None:
        """Add a sequencer row with the given settings."""
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

    def split(self, count: int) -> SequencerRows:
        """Truncate this object after `count` rows, and return the remainder.

        We need the final row of this object to have a count of 1 in order to subtract
        the table switch delay."""

        assert len(self._rows) > 0, "Zero length seq rows should never be split"

        if len(self._rows) >= count:
            final_row = self._rows[count - 1]
            if final_row.repeats == 0:  # Final row in continuous loop
                assert len(self._rows) == count  # Continuous loop always at end
                return SequencerRows()

            if final_row.repeats == 1:
                remainder = SequencerRows(self._rows[count:])
                self._rows = self._rows[:count]

            elif final_row.repeats > 1:
                remainder = SequencerRows(
                    [final_row._replace(repeats=final_row.repeats - 1)]
                )
                remainder.extend(SequencerRows(self._rows[count:]))
                self._rows = self._rows[: count - 1]
                self._rows.append(final_row._replace(repeats=1))
        else:
            remainder = SequencerRows()

            if self._rows[-1].repeats == 0:
                return remainder

            if self._rows[-1].repeats > 1:
                final_row = self._rows[-1]
                self._rows[-1] = final_row._replace(repeats=final_row.repeats - 1)
                self._rows += [final_row._replace(repeats=1)]

        final_self_row = self._rows[-1]
        self._rows[-1] = final_self_row._replace(
            time2=final_self_row.time2 - SEQ_TABLE_SWITCH_DELAY
        )
        self._duration -= SEQ_TABLE_SWITCH_DELAY
        self._duration -= remainder.duration
        return remainder

    def extend(self, other: SequencerRows) -> None:
        """Extend this object by the given `SequencerRows` object."""
        self._rows += other._rows
        self._duration += other._duration

    def get_table(self) -> SequencerTable:
        """Return a `SequencerTable` from this object's rows."""
        return SequencerTable.from_rows(self._rows)

    def as_tuples(self) -> Tuple[Tuple, ...]:
        """Return the sequencer rows as a tuple of tuples.

        This is used for comparisons during testing.
        """
        return tuple(self._rows)

    @property
    def duration(self) -> float:
        """Return the total duration of all Sequencer rows."""
        return self._duration * TICK

    def __len__(self) -> int:
        """Return the number of Sequencer rows."""
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
    ) -> SequencerRow:
        """Create a pulse with phase1 having the given live/dead values.

        If trim=0, there is a 50% duty cycle. Trim (in ticks) reduces total duration by
        subtracting ticks from the phase2 time.
        """
        return SequencerRow(
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
    def _calculate_duration(rows: List[SequencerRow]) -> float:
        """Return the duration of the given Sequencer rows (in list format)."""
        duration = 0.0
        for row in rows:
            duration += row.repeats * (row.time1 + row.time2)

        return duration


class DoubleBuffer:
    """A class that uses two Sequencer (SEQ) blocks in a double buffering system."""

    def __init__(self, context: Context, seq_a: Block, seq_b: Block) -> None:
        self._context: Context = context
        # Need to replace Block with Any due to limitations of typing in malcolm core
        self._table_map: Dict[str, Any] = {"seqA": seq_a, "seqB": seq_b}
        self._seq_status: Dict[str, Optional[bool]] = {"seqA": None, "seqB": None}
        self._futures: List[Future] = []
        self._finished: bool = True
        self._table_gen: Iterator[SequencerTable] = iter(())

    def _fill_table(self, table, gen) -> None:
        """Fill the given Sequencer table using the given generator."""
        seq_table = self._table_map[table]
        seq_table.table.put_value(next(gen))

    @staticmethod
    def _get_tables(rows_gen: Iterator[SequencerRows]) -> Iterator[SequencerTable]:
        """Yield a series of SequencerTable objects from the given rows generator.

        This generator ensures that each SequencerTable can fit onto a SEQ block.
        """
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

    def configure(self, rows_generator: Iterator[SequencerRows]) -> None:
        """Configure the double buffer object.

        This is designed to be called as part of the malcolm configure process.
        """
        self.clean_up()
        self._table_gen = self._get_tables(rows_generator)

        try:
            self._fill_table("seqA", self._table_gen)
            self._fill_table("seqB", self._table_gen)
        except StopIteration:
            self._finished = True
        else:
            # More than 1 sequencer table is required so repeats must be 1.
            # The template sets repeats to 1 however older designs may not have
            # been updated.
            for table in self._table_map.values():
                table.repeats.put_value(1)
            self._finished = False

    def _seq_active_handler(self, value: bool, table: str = "seqA") -> None:
        """Handler for the SEQ block activation subscription."""
        prev = self._seq_status[table]
        if prev is not None and prev and not value:
            # We only care when the seq is deactivated
            try:
                self._fill_table(table, self._table_gen)
            except StopIteration:
                self.clean_up()
                return

        self._seq_status[table] = value

    def _setup_subscriptions(self) -> None:
        """Set up subscriptions to the SEQ block 'active' field."""
        for table in self._table_map:
            self._futures += [
                self._table_map[table].active.subscribe_value(
                    self._seq_active_handler, table
                )
            ]

    def run(self) -> List[Future]:
        """Start the double buffering system."""
        if not self._finished:
            self._setup_subscriptions()

        return self._futures

    def _remove_subscriptions(self) -> None:
        """Remove all subscriptions in this `DoubleBuffer` object."""
        for future in self._futures:
            self._context.unsubscribe(future)

        self._futures = []

    def clean_up(self) -> None:
        """Clean up in preparation for the next scan."""
        self._remove_subscriptions()
        self._seq_status = {"seqA": None, "seqB": None}
        self._finished = True
