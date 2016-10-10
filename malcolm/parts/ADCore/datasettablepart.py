from collections import OrderedDict, namedtuple

from malcolm.core import Part, Table
from malcolm.core.vmetas import StringArrayMeta, ChoiceArrayMeta, TableMeta
from malcolm.controllers.runnablecontroller import RunnableController

# Make a table for the dataset info we produce
columns = OrderedDict()
columns["name"] = StringArrayMeta("Dataset name")
columns["filename"] = StringArrayMeta("Filename of HDF file")
columns["type"] = ChoiceArrayMeta("Type of dataset", ["primary", "additional"])
columns["path"] = StringArrayMeta("Dataset path within HDF file")
columns["uniqueid"] = StringArrayMeta("UniqueID array path within HDF file")
dataset_table_meta = TableMeta("Datsets produced in HDF file", columns=columns)

# Produced by plugins in part_info
DatasetProducedInfo = namedtuple("DatasetProducedInfo", columns)


class DatasetTablePart(Part):
    # Created attributes
    datasets = None

    def create_attributes(self):
        for data in super(DatasetTablePart, self).create_attributes():
            yield data
        self.datasets = dataset_table_meta.make_attribute()
        yield "datasets", self.datasets, None

    @RunnableController.PostConfigure
    def update_datasets_table(self, _, part_info):
        # Update the dataset table
        datasets_table = Table(dataset_table_meta)
        for dataset_infos in part_info.values():
            for dataset_info in dataset_infos:
                row = list(dataset_info)
                datasets_table.append(row)
        self.datasets.set_value(datasets_table)
