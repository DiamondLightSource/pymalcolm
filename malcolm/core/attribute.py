from collections import OrderedDict

from malcolm.core.notifier import Notifier, NO_VALIDATE
from malcolm.core.serializable import Serializable
from malcolm.metas.scalarmeta import ScalarMeta


@Serializable.register_subclass("epics:nt/NTAttribute:1.0")
class Attribute(Notifier):
    """Represents a value with type information that may be backed elsewhere"""

    endpoints = ["meta", "value"]

    def __init__(self, meta=None):
        self.value = None
        self.put_func = None
        if meta is None:
            self.meta = None
        else:
            self.set_meta(meta)

    def set_meta(self, meta, notify=True):
        """Set the ScalarMeta object"""
        self.set_endpoint(ScalarMeta, "meta", meta, notify)

    def set_put_function(self, func):
        self.put_func = func

    def put(self, value):
        """Call the put function with the given value"""
        self.put_func(value)

    def set_value(self, value, notify=True):
        value = self.meta.validate(value)
        self.set_endpoint(NO_VALIDATE, "value", value, notify)
