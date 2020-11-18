from typing import List

from malcolm.core import PartRegistrar
from malcolm.modules import ADCore, pandablocks, scanning

from ..util import DatasetBitsTable, DatasetPositionsTable


class PandADatasetBussesPart(pandablocks.parts.PandABussesPart):
    bits_table_cls = DatasetBitsTable
    positions_table_cls = DatasetPositionsTable

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)

    @staticmethod
    def _make_initial_bits_table(bit_names: List[str]) -> DatasetBitsTable:
        ds_types = [ADCore.util.AttributeDatasetType.MONITOR] * len(bit_names)
        bits_table = DatasetBitsTable(
            name=bit_names,
            value=[False] * len(bit_names),
            capture=[False] * len(bit_names),
            datasetName=[""] * len(bit_names),
            datasetType=ds_types,
        )
        return bits_table

    @staticmethod
    def _make_initial_pos_table(pos_names: List[str]) -> DatasetPositionsTable:
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
            datasetType=ds_types,
        )
        return pos_table

    def on_report_status(self) -> scanning.hooks.UInfos:
        ret = []
        assert self.bits, "No bits"
        bits_table: DatasetBitsTable = self.bits.value
        for i, capture in enumerate(bits_table.capture):
            ds_name = bits_table.datasetName[i]
            if ds_name and capture:
                ret.append(
                    ADCore.infos.NDAttributeDatasetInfo.from_attribute_type(
                        name=ds_name,
                        type=bits_table.datasetType[i],
                        attr=bits_table.name[i],
                    )
                )
        assert self.positions, "No positions"
        pos_table: DatasetPositionsTable = self.positions.value
        for i, capture in enumerate(pos_table.capture):
            ds_name = pos_table.datasetName[i]
            if ds_name and capture != pandablocks.util.PositionCapture.NO:
                suffixes: List[str] = capture.value.split(" ")
                # If we have multiple values, export Min and Max as such
                if len(suffixes) > 1:
                    for suffix in [x for x in ("Min", "Max") if x in suffixes]:
                        suffixes.remove(suffix)
                        type_name = "POSITION_%s" % suffix.upper()
                        ret.append(
                            ADCore.infos.NDAttributeDatasetInfo(
                                name="%s.%s" % (ds_name, suffix.lower()),
                                type=scanning.util.DatasetType[type_name],
                                attr="%s.%s" % (pos_table.name[i], suffix),
                            )
                        )
                # There should now be 1 or 0 suffixes left to report
                if suffixes:
                    assert len(suffixes) == 1, (
                        "Cannot deal with capture value %r" % capture.value
                    )
                    suffix = suffixes[0]
                    ret.append(
                        ADCore.infos.NDAttributeDatasetInfo.from_attribute_type(
                            name=ds_name,
                            type=pos_table.datasetType[i],
                            attr="%s.%s" % (pos_table.name[i], suffix),
                        )
                    )
        return ret
