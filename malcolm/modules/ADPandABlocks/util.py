from typing import Union

import numpy as np
from annotypes import Anno, Array

from malcolm.core import Table
from malcolm.modules import ADCore, pandablocks


class Trigger:
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
    ALineRepeatsArray = Union[Array[np.uint16]]
with Anno("The trigger condition to start the phases"):
    ATriggerArray = Union[Array[str]]
with Anno("The position that can be used in trigger condition"):
    APositionArray = Union[Array[np.int32]]
with Anno("The time that the phase should take"):
    ATimeArray = Union[Array[np.uint32]]
with Anno("Output value during the phase"):
    AOutArray = Union[Array[bool]]

# TODO - WHAT GIVES HERE ?? -
#  AAttributeNames and AAttributeNames causes an IDE error in references below
#  wheras "from ADCore.util import AAttributeTypes" does not
# Pull re-used annotypes into our namespace in case we are subclassed
AAttributeTypes = ADCore.util.AAttributeTypes
UAttributeTypes = ADCore.util.UAttributeTypes
AAttributeNames = ADCore.util.AAttributeNames
UAttributeNames = ADCore.util.UAttributeNames
UBitNames = pandablocks.util.UBitNames
UBitValues = pandablocks.util.UBitValues
UBitCaptures = pandablocks.util.UBitCaptures
UPositionNames = pandablocks.util.UPositionNames
UPositionValues = pandablocks.util.UPositionValues
UPositionUnits = pandablocks.util.UPositionUnits
UPositionScales = pandablocks.util.UPositionScales
UPositionOffsets = pandablocks.util.UPositionOffsets
UPositionCaptures = pandablocks.util.UPositionCaptures


class SequencerTable(Table):
    """Convenience Table object for building sequencer tables"""

    def __init__(
        self,
        repeats: ALineRepeatsArray,
        trigger: ATriggerArray,
        position: APositionArray,
        time1: ATimeArray,
        outa1: AOutArray,
        outb1: AOutArray,
        outc1: AOutArray,
        outd1: AOutArray,
        oute1: AOutArray,
        outf1: AOutArray,
        time2: ATimeArray,
        outa2: AOutArray,
        outb2: AOutArray,
        outc2: AOutArray,
        outd2: AOutArray,
        oute2: AOutArray,
        outf2: AOutArray,
    ) -> None:
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


class DatasetBitsTable(pandablocks.util.BitsTable):
    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    def __init__(
        self,
        name: UBitNames,
        value: UBitValues,
        capture: UBitCaptures,
        datasetName: UAttributeNames,
        datasetType: UAttributeTypes,
    ) -> None:
        super().__init__(name, value, capture)
        self.datasetName = AAttributeNames(datasetName)
        self.datasetType = AAttributeTypes(datasetType)


class DatasetPositionsTable(pandablocks.util.PositionsTable):
    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    def __init__(
        self,
        name: UPositionNames,
        value: UPositionValues,
        units: UPositionUnits,
        scale: UPositionScales,
        offset: UPositionOffsets,
        capture: UPositionCaptures,
        datasetName: UAttributeNames,
        datasetType: UAttributeTypes,
    ) -> None:
        super().__init__(name, value, units, scale, offset, capture)
        self.datasetName = AAttributeNames(datasetName)
        self.datasetType = AAttributeTypes(datasetType)
