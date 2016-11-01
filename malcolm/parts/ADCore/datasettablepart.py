from malcolm.compat import OrderedDict
from malcolm.core import Part, Table, Info
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
class DatasetProducedInfo(Info):
    def __init__(self, name, filename, type, path, uniqueid):
        self.name = name
        self.filename = filename
        self.type = type
        self.path = path
        self.uniqueid = uniqueid


class DatasetTablePart(Part):
    # Created attributes
    datasets = None

    def create_attributes(self):
        self.datasets = dataset_table_meta.make_attribute()
        yield "datasets", self.datasets, None

    @RunnableController.PostConfigure
    def update_datasets_table(self, task, part_info):
        # Update the dataset table
        datasets_table = Table(dataset_table_meta)
        for dataset_infos in DatasetProducedInfo.filter(part_info).values():
            for i in dataset_infos:
                row = [i.name, i.filename, i.type, i.path, i.uniqueid]
                datasets_table.append(row)
        self.datasets.set_value(datasets_table)
