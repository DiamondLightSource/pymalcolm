from malcolm.compat import OrderedDict
from malcolm.core import Part, Table, method_takes, REQUIRED
from malcolm.modules.ADCore.infos import DatasetProducedInfo, dataset_types
from malcolm.modules.builtin.vmetas import StringArrayMeta, ChoiceArrayMeta, \
    TableMeta, NumberArrayMeta, StringMeta
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.tags import widget

# Make a table for the dataset info we produce
columns = OrderedDict()
columns["name"] = StringArrayMeta("Dataset name")
columns["filename"] = StringArrayMeta(
    "Filename of HDF file relative to fileDir")
columns["type"] = ChoiceArrayMeta("Type of dataset", dataset_types)
columns["rank"] = NumberArrayMeta("int32", "Rank (number of dimensions)")
columns["path"] = StringArrayMeta("Dataset path within HDF file")
columns["uniqueid"] = StringArrayMeta("UniqueID array path within HDF file")
dataset_table_meta = TableMeta(
    "Datsets produced in HDF file", elements=columns, tags=[widget("table")])

@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED)
class DatasetTablePart(Part):
    """Exposes an Attribute that reports the datasets that will be written
    during a scan"""
    def __init__(self, params):
        # Created attributes
        self.datasets = None
        super(DatasetTablePart, self).__init__(params.name)

    def create_attribute_models(self):
        # Create read-only attribute showing the datasets we are creating
        self.datasets = dataset_table_meta.create_attribute_model()
        yield "datasets", self.datasets, None

    @RunnableController.PostConfigure
    def update_datasets_table(self, context, part_info):
        # Update the dataset table
        datasets_table = Table(dataset_table_meta)
        for i in DatasetProducedInfo.filter_values(part_info):
            if i.name not in datasets_table.name:
                row = [i.name, i.filename, i.type, i.rank, i.path, i.uniqueid]
                datasets_table.append(row)
        self.datasets.set_value(datasets_table)
