from annotypes import Anno, Array
from enum import Enum
import numpy as np

from malcolm.core import Table


class Trigger(object):
    """Convenience Enum for setting sequencer tables, will be translated into
    integer values by the TablePart. The strings must match what comes from the
    PandA"""
    IMMEDIATE = "Immediate"
    BITA_0 = "BITA=0"
    BITA_1 = "BITA=1"
    BITB_0 = "BITB=0"
    BITB_1 = "BITB=1"
    BITC_0 = "BITC=0"
    BITC_1 = "BITC=1"
    POSA_GT = "POSA>=POSITION"
    POSA_LT = "POSA<=POSITION"
    POSB_GT = "POSB>=POSITION"
    POSB_LT = "POSB<=POSITION"
    POSC_GT = "POSC>=POSITION"
    POSC_LT = "POSC<=POSITION"


with Anno("Number of times the line will repeat"):
    ALineRepeatsArray = Array[np.uint16]
with Anno("The trigger condition to start the phases"):
    ATriggerArray = Array[str]
with Anno("The position that can be used in trigger condition"):
    APositionArray = Array[np.int32]
with Anno("The time that the phase should take"):
    ATimeArray = Array[np.uint32]
with Anno("Output value during the phase"):
    AOutArray = Array[bool]


class SequencerTable(Table):
    """Convenience Table object for building sequencer tables"""
    def __init__(self,
                 repeats,  # type: ALineRepeatsArray
                 trigger,  # type: ATriggerArray
                 position,  # type: APositionArray
                 time1,  # type: ATimeArray
                 outa1,  # type: AOutArray
                 outb1,  # type: AOutArray
                 outc1,  # type: AOutArray
                 outd1,  # type: AOutArray
                 oute1,  # type: AOutArray
                 outf1,  # type: AOutArray
                 time2,  # type: ATimeArray
                 outa2,  # type: AOutArray
                 outb2,  # type: AOutArray
                 outc2,  # type: AOutArray
                 outd2,  # type: AOutArray
                 oute2,  # type: AOutArray
                 outf2,  # type: AOutArray
                 ):
        # type: (...) -> None
        self.repeats = ALineRepeatsArray(repeats)
        self.trigger = ATriggerArray(trigger)
        self.position = APositionArray(position)
        self.time1 = ATimeArray(time1)
        self.outa1 = AOutArray(outa1)
        self.outb1 = AOutArray(outb1)
        self.outc1 = AOutArray(outc1)
        self.outd1 = AOutArray(outd1)
        self.oute1 = AOutArray(oute1)
        self.outf1 = AOutArray(outf1)
        self.time2 = ATimeArray(time2)
        self.outa2 = AOutArray(outa2)
        self.outb2 = AOutArray(outb2)
        self.outc2 = AOutArray(outc2)
        self.outd2 = AOutArray(outd2)
        self.oute2 = AOutArray(oute2)
        self.outf2 = AOutArray(outf2)
