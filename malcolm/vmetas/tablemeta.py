from collections import OrderedDict

from malcolm.compat import base_string
from malcolm.core import Serializable, Table, VArrayMeta, VMeta


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):

    endpoints = ["elements", "description", "tags",
                 "writeable", "label", "headings"]

    def __init__(self, description="", tags=None, writeable=False, label=""):
        super(TableMeta, self).__init__(description, tags, writeable, label)
        self.set_headings([])
        self.elements = OrderedDict()

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarArrayMeta or serialized dict"""
        self.set_endpoint(
            {base_string: VArrayMeta}, "elements", elements, notify)

    def set_headings(self, headings, notify=True):
        """Set the headings list"""
        self.set_endpoint([base_string], "headings", headings, notify)

    def validate(self, value):
        if not isinstance(value, Table):
            # turn it into a table
            value = Table.from_dict(value, meta=self)
        else:
            # Check that it's using the same meta object
            assert self == value.meta, \
                "Supplied table with wrong meta type"
        # Check column lengths
        value.verify_column_lengths()
        return value
