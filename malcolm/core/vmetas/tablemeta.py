from malcolm.core.nttable import NTTable
from malcolm.core.serializable import Serializable, deserialize_object
from malcolm.core.table import Table
from malcolm.core.tableelementmap import TableElementMap
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):

    endpoints = ["elements", "description", "tags", "writeable", "label"]
    attribute_class = NTTable

    def __init__(self, description="", tags=None, writeable=False, label="",
                 columns=None):
        super(TableMeta, self).__init__(description, tags, writeable, label)
        if columns is None:
            columns = {}
        self.set_elements(TableElementMap(columns))

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarArrayMeta or serialized dict"""
        elements = deserialize_object(elements, TableElementMap)
        self.set_endpoint_data("elements", elements, notify)

    def validate(self, value):
        if value is None:
            value = {}
        if isinstance(value, Table):
            if self != value.meta:
                # Make a table using ourself as the meta
                value = value.to_dict()
                value.pop("typeid", None)
                value = Table(self, value)
        else:
            # Should be a dict
            value = Table(self, value)
        # Check column lengths
        value.verify_column_lengths()
        return value
