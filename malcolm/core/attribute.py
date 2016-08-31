from malcolm.core.monitorable import Monitorable
from malcolm.core.request import Put
from malcolm.core.serializable import Serializable, deserialize_object
from malcolm.core.vmeta import VMeta


# TODO: use NTScalar, NTScalarArray, NTTable and NTUnion here. Metas can create
@Serializable.register_subclass("epics:nt/NTAttribute:1.0")
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
        meta = deserialize_object(meta, VMeta)
        self.set_endpoint_data("meta", meta, notify)

    def set_value(self, value, notify=True):
        value = self.meta.validate(value)
        self.set_endpoint_data("value", value, notify)

    def handle_request(self, request, put_function):
        assert isinstance(request, Put), "Expected Put, got %r" % (request,)
        assert len(request.endpoint) == 3 and request.endpoint[-1] == "value", \
            "Can only Put to Attribute value, not %s" % (request.endpoint,)
        put_function(self.meta, request.value)
