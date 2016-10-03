from malcolm.core.monitorable import Monitorable
from malcolm.core.request import Put
from malcolm.core.serializable import deserialize_object


class Attribute(Monitorable):
    """Represents a value with type information that may be backed elsewhere"""

    endpoints = ["meta", "value"]

    def __init__(self, meta=None, value=None):
        if meta is None:
            self.set_endpoint_data("meta", None)
        else:
            self.set_meta(meta)
        if value is None:
            self.set_endpoint_data("value", None)
        else:
            self.set_value(value)

    def set_meta(self, meta, notify=True):
        """Set the VMeta object"""
        meta = deserialize_object(meta)
        # Check that the meta attribute_class is ourself
        assert hasattr(meta, "attribute_class"), \
            "Expected meta object, got %r" % meta
        assert isinstance(self, meta.attribute_class), \
            "Meta object needs to be attached to %s, we are a %s" % (
                meta.attribute_class, type(self))
        self.set_endpoint_data("meta", meta, notify)

    def set_value(self, value, notify=True):
        value = self.meta.validate(value)
        self.set_endpoint_data("value", value, notify)

    def handle_request(self, request, put_function):
        assert isinstance(request, Put), "Expected Put, got %r" % (request,)
        assert len(request.endpoint) == 3 and request.endpoint[-1] == "value", \
            "Can only Put to Attribute value, not %s" % (request.endpoint,)
        put_function(self.meta, request.value)
