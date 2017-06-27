from malcolm.compat import str_, OrderedDict
from malcolm.core import NTTable, Serializable, deserialize_object, Table, \
    VMeta, VArrayMeta


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):

    endpoints = ["elements", "description", "tags", "writeable", "label"]
    attribute_class = NTTable

    def __init__(self, description="", tags=(), writeable=False, label="",
                 elements=None):
        super(TableMeta, self).__init__(description, tags, writeable, label)
        if elements is None:
            elements = {}
        self.elements = self.set_elements(elements)

    def set_elements(self, elements):
        """Set the elements dict from a serialized dict"""
        deserialized = OrderedDict()
        for k, v in elements.items():
            if k != "typeid":
                k = deserialize_object(k, str_)
                deserialized[k] = deserialize_object(v, VArrayMeta)
        return self.set_endpoint_data("elements", deserialized)

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

    def doc_type_string(self):
        return "`Table`"
