from annotypes import TYPE_CHECKING

from malcolm.core import PartRegistrar
from malcolm.modules import scanning, ADCore, pandablocks
from ..util import DatasetBitsTable, DatasetPositionsTable

if TYPE_CHECKING:
    from typing import List


class PandADatasetBussesPart(pandablocks.parts.PandABussesPart):
    bits_table_cls = DatasetBitsTable
    positions_table_cls = DatasetPositionsTable

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandADatasetBussesPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook,
                       self.report_status)

    @staticmethod
    def _make_initial_bits_table(bit_names):
        # type: (List[str]) -> DatasetBitsTable
        ds_types = [ADCore.util.AttributeDatasetType.MONITOR] * len(bit_names)
        bits_table = DatasetBitsTable(
            name=bit_names,
            value=[False] * len(bit_names),
            capture=[False] * len(bit_names),
            datasetName=[""] * len(bit_names),
            datasetType=ds_types
        )
        return bits_table

    @staticmethod
    def _make_initial_pos_table(pos_names):
        # type: (List[str]) -> DatasetPositionsTable
        ds_types = []
        for pos in pos_names:
            if pos.startswith("INENC"):
                ds_types.append(ADCore.util.AttributeDatasetType.POSITION)
            else:
                ds_types.append(ADCore.util.AttributeDatasetType.MONITOR)
        pos_table = DatasetPositionsTable(
            name=pos_names,
            value=[0.0] * len(pos_names),
            units=[""] * len(pos_names),
            scale=[1.0] * len(pos_names),
            offset=[0.0] * len(pos_names),
            capture=[pandablocks.util.PositionCapture.NO] * len(pos_names),
            datasetName=[""] * len(pos_names),
            datasetType=ds_types
        )
        return pos_table

    def report_status(self):
        # type: () -> scanning.hooks.UInfos
        ret = []
        bits_table = self.bits.value  # type: DatasetBitsTable
        for i, capture in enumerate(bits_table.capture):
            if capture:
                ret.append(ADCore.infos.NDAttributeDatasetInfo(
                    name=bits_table.datasetName[i],
                    type=bits_table.datasetType[i],
                    rank=2,
                    attr=bits_table.name[i]))
        pos_table = self.positions.value  # type: DatasetPositionsTable
        for i, capture in enumerate(pos_table.capture):
            ds_name = pos_table.datasetName[i]
            if ds_name and capture != pandablocks.util.PositionCapture.NO:
                info = None
                capture_split = capture.value.split(" ")
                for suffix in capture_split:
                    info = ADCore.infos.NDAttributeDatasetInfo.\
                        from_attribute_type(
                            name=ds_name,
                            type=pos_table.datasetType[i],
                            attr="%s.%s" % (pos_table.name[i], suffix),
                            rank=2)
                    # Override special cases
                    if type == ADCore.infos.AttributeDatasetType.POSITION:
                        if suffix == "Min":
                            info.name = "%s.min" % ds_name
                            info.type = scanning.infos.DatasetType.POSITION_MIN
                        if suffix == "Max":
                            info.name = "%s.max" % ds_name
                            info.type = scanning.infos.DatasetType.POSITION_MAX
                if info:
                    ret.append(info)
        return ret
