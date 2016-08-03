from malcolm.core.monitorable import Monitorable, NO_VALIDATE
from malcolm.core.serializable import Serializable
from malcolm.core.request import Put
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("epics:nt/NTAttribute:1.0")
class Attribute(Monitorable):
    """Represents a value with type information that may be backed elsewhere"""

    endpoints = ["meta", "value"]

    def __init__(self, meta=None, value=None):
        if meta is None:
            self.meta = None
        else:
            self.set_meta(meta)
        if value is None:
            self.value = None
        else:
            self.set_value(value)

    def set_meta(self, meta, notify=True):
        """Set the ScalarMeta object"""
        self.set_endpoint(VMeta, "meta", meta, notify)

    def handle_request(self, request, put_function):
        self.log_debug("Received request %s", request)
        assert isinstance(request, Put), "Expected Put, got %r" % (request,)
        assert len(request.endpoint) == 3 and request.endpoint[-1] == "value", \
            "Can only Put to Attribute value, not %s" % (request.endpoint,)
        put_function(self, request.value)

    def set_value(self, value, notify=True):
        value = self.meta.validate(value)
        self.set_endpoint(NO_VALIDATE, "value", value, notify)
