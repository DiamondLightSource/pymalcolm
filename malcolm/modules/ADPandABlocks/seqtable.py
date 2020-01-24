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


class SequencerRows:
    def __init__(self, rows=None):
        self._rows = rows if rows else []

    def add_seq_entry(self, count=1, trigger=Trigger.IMMEDIATE, position=0,
                      half_duration=MIN_PULSE, live=0, dead=0, trim=0):
        complete_rows = count // MAX_REPEATS
        remaining = count % MAX_REPEATS

        row = self._seq_row(MAX_REPEATS, trigger, position, half_duration, live,
                            dead, trim)
        self._rows.extend(row * complete_rows)
        self._rows.append(self._seq_row(remaining, trigger, position,
                                        half_duration, live, dead, trim))

    def extend(self, other):
        self._rows += other._rows

    def get_table(self):
        return SequencerTable.from_rows(self._rows)

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
