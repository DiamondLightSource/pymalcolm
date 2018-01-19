from annotypes import add_call_types

from malcolm.compat import OrderedDict
from malcolm.core import Part, Hook, PartRegistrar, APartName, TableMeta
from malcolm.modules import scanning
from ..infos import DatasetProducedInfo
from ..util import DatasetTable


class DatasetTablePart(Part):
    """Exposes an Attribute that reports the datasets that will be written
    during a scan"""
    def __init__(self, name):
        # type: (APartName) -> None
        super(DatasetTablePart, self).__init__(name)
        self.datasets = TableMeta.from_table(
            DatasetTable, "Datasets produced in HDF file"
        ).create_attribute_model()

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model("datasets", self.datasets)

    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(hook, scanning.hooks.PostConfigureHook):
            hook(self.post_configure)

    @add_call_types
    def post_configure(self, part_info):
        # type: (scanning.hooks.APartInfo) -> None
        # Update the dataset table
        rows = OrderedDict()
        for i in DatasetProducedInfo.filter_values(part_info):
            if i.name not in rows:
                row = [i.name, i.filename, i.type, i.rank, i.path, i.uniqueid]
                rows[i.name] = row
        datasets_table = DatasetTable.from_rows(rows)
        self.datasets.set_value(datasets_table)
