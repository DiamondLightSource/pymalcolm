from malcolm.compat import OrderedDict
from malcolm.core import Part, Table, Info
from malcolm.core.vmetas import StringArrayMeta, ChoiceArrayMeta, TableMeta, \
    NumberArrayMeta
from malcolm.controllers.runnablecontroller import RunnableController

# Make a table for the dataset info we produce
dataset_types = [
    "primary", "secondary", "monitor", "position_set", "position_value"]
columns = OrderedDict()
columns["name"] = StringArrayMeta("Dataset name")
columns["filename"] = StringArrayMeta(
    "Filename of HDF file relative to fileDir")
columns["type"] = ChoiceArrayMeta("Type of dataset", dataset_types)
columns["rank"] = NumberArrayMeta("uint8", "Rank (number of dimensions)")
columns["path"] = StringArrayMeta("Dataset path within HDF file")
columns["uniqueid"] = StringArrayMeta("UniqueID array path within HDF file")
dataset_table_meta = TableMeta("Datsets produced in HDF file", columns=columns)


# Produced by plugins in part_info
class DatasetProducedInfo(Info):
    def __init__(self, name, filename, type, rank, path, uniqueid):
        self.name = name
        self.filename = filename
        assert type in dataset_types, \
            "Dataset type %s not in %s" % (type, dataset_types)
        self.type = type
        self.rank = rank
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
        for i in DatasetProducedInfo.filter_values(part_info):
            row = [i.name, i.filename, i.type, i.rank, i.path, i.uniqueid]
            datasets_table.append(row)
        self.datasets.set_value(datasets_table)
