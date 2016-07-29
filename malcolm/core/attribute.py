from collections import OrderedDict

from malcolm.core.notifier import Notifier
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
        if isinstance(meta, dict):
            meta = Serializable.from_dict(meta)
        assert isinstance(meta, ScalarMeta), \
            "Expected meta to be a ScalarMeta subclass, got %s" % (meta,)
        meta.set_parent(self, "meta")
        self.set_endpoint("meta", meta, notify)

    def set_put_function(self, func):
        self.put_func = func

    def put(self, value):
        """Call the put function with the given value"""
        self.put_func(value)

    def set_value(self, value, notify=True):
        value = self.meta.validate(value)
        self.set_endpoint("value", value, notify)
