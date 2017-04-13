from malcolm.compat import str_
from .meta import Meta
from .serializable import Serializable, deserialize_object
from .stringarray import StringArray


@Serializable.register_subclass("malcolm:core/BlockMeta:1.0")
class BlockMeta(Meta):
    endpoints = ["description", "tags", "writeable", "label", "fields"]

    def __init__(self, description="", tags=(), writeable=False, label="",
                 fields=()):
        super(BlockMeta, self).__init__(description, tags, writeable, label)
        # Set initial values
        self.fields = self.set_fields(fields)

    def set_fields(self, fields):
        """Set the fields StringArray"""
        fields = StringArray(deserialize_object(f, str_) for f in fields)
        return self.set_endpoint_data("fields", fields)
