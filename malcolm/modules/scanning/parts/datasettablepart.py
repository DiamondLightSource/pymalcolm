from annotypes import add_call_types

from malcolm.core import AttributeModel, Part, PartRegistrar, TableMeta
from malcolm.modules import builtin

from ..hooks import APartInfo, PostConfigureHook
from ..infos import DatasetProducedInfo
from ..util import DatasetTable


class DatasetTablePart(Part):
    """Exposes an Attribute that reports the datasets that will be written
    during a scan"""

    datasets: AttributeModel = None

    def setup(self, registrar: PartRegistrar) -> None:
        self.datasets = TableMeta.from_table(
            DatasetTable, "Datasets produced in HDF file"
        ).create_attribute_model()
        registrar.add_attribute_model("datasets", self.datasets)
        # Hooks
        registrar.hook(PostConfigureHook, self.on_post_configure)
        registrar.hook(builtin.hooks.ResetHook, self.on_reset)

    @add_call_types
    def on_post_configure(self, part_info: APartInfo) -> None:
        # Update the dataset table
        name, filename, typ, rank, path, uid = [], [], [], [], [], []
        for i in DatasetProducedInfo.filter_values(part_info):
            name.append(i.name)
            filename.append(i.filename)
            typ.append(i.type)
            rank.append(i.rank)
            path.append(i.path)
            uid.append(i.uniqueid)
        datasets_table = DatasetTable(name, filename, typ, rank, path, uid)
        self.datasets.set_value(datasets_table)

    def on_reset(self):
        self.datasets.set_value(None)
