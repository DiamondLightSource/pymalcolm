from malcolm.compat import str_
from malcolm.core import NTTable, Serializable, deserialize_object, Table, \
    VMeta, VArrayMeta


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):

    endpoints = ["elements", "description", "tags", "writeable", "label"]
    attribute_class = NTTable

    def __init__(self, description="", tags=None, writeable=False, label="",
                 elements=None):
        super(TableMeta, self).__init__(description, tags, writeable, label)
        if elements is None:
            elements = {}
        self.elements = self.set_elements(elements)

    def set_elements(self, elements):
        """Set the elements dict from a serialized dict"""
        for k, v in elements.items():
            k = deserialize_object(k, str_)
            elements[k] = deserialize_object(v, VArrayMeta)
        return self.set_endpoint_data("elements", elements)

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
