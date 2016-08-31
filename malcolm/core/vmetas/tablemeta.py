from malcolm.compat import str_
from malcolm.core.serializable import Serializable, deserialize_object
from malcolm.core.table import Table
from malcolm.core.tableelementmap import TableElementMap
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):

    endpoints = ["elements", "description", "tags", "writeable", "label",
                 "headings"]

    def __init__(self, description="", tags=None, writeable=False, label="",
                 columns=None):
        super(TableMeta, self).__init__(description, tags, writeable, label)
        if columns is None:
            columns = {}
        self.set_elements(TableElementMap(columns))
        self.set_headings([])

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarArrayMeta or serialized dict"""
        elements = deserialize_object(elements, TableElementMap)
        self.set_endpoint_data("elements", elements, notify)

    def set_headings(self, headings, notify=True):
        """Set the headings list"""
        headings = [deserialize_object(h, str_) for h in headings]
        self.set_endpoint_data("headings", headings, notify)

    def validate(self, value):
        if not isinstance(value, Table):
            # turn it into a table
            value.pop("typeid")
            value = Table(self, value)
        else:
            # Check that it's using the same meta object
            assert self == value.meta, \
                "Supplied table with wrong meta type"
        # Check column lengths
        value.verify_column_lengths()
        return value
