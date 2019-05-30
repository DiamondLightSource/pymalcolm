from annotypes import add_call_types

from malcolm.core import Part, PartRegistrar, TableMeta, AttributeModel
from ..infos import DatasetProducedInfo
from ..util import DatasetTable
from ..hooks import PostConfigureHook, APartInfo


class DatasetTablePart(Part):
    """Exposes an Attribute that reports the datasets that will be written
    during a scan"""
    datasets = None  # type: AttributeModel

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.datasets = TableMeta.from_table(
            DatasetTable, "Datasets produced in HDF file"
        ).create_attribute_model()
        registrar.add_attribute_model("datasets", self.datasets)
        # Hooks
        registrar.hook(PostConfigureHook, self.post_configure)

    @add_call_types
    def post_configure(self, part_info):
        # type: (APartInfo) -> None
        # Update the dataset table
        name, filename, typ, rank, path, uid = [], [], [], [], [], []
        for i in DatasetProducedInfo.filter_values(part_info):
            if i.name not in name:
                name.append(i.name)
                filename.append(i.filename)
                typ.append(i.type)
                rank.append(i.rank)
                path.append(i.path)
                uid.append(i.uniqueid)
        datasets_table = DatasetTable(name, filename, typ, rank, path, uid)
        self.datasets.set_value(datasets_table)
