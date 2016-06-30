from collections import OrderedDict

from malcolm.core.attributemeta import AttributeMeta
from malcolm.core.serializable import Serializable


@Serializable.register("epics:nt/NTAttribute:1.0")
class Attribute(Serializable):
    """Represents a value with type information that may be backed elsewhere"""

    def __init__(self, name, meta):
        super(Attribute, self).__init__(name)
        if meta.name != "meta":
            raise ValueError(
                "Meta name must be 'meta' to be added to an Attribute")
        self.meta = meta
        self.value = None
        self.put_func = None

    def set_put_function(self, func):
        self.put_func = func

    def put(self, value):
        """Call the put function with the given value"""
        self.put_func(value)

    def set_value(self, value):
        self.value = value
        self.on_changed([["value"], value])

    def to_dict(self):
        """Create ordered dictionary representing class instance"""
        d = OrderedDict()
        d["value"] = self.value
        d["meta"] = self.meta.to_dict()
        d["typeid"] = self.typeid
        # TODO: add timeStamp and alarm
        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create an Attribute instance from a serialized version of itself

        Args:
            name (str): Attribute instance name
            d (dict): Output of self.to_dict()
        """
        meta = AttributeMeta.from_dict("meta", d["meta"])
        attribute = cls(name, meta)
        attribute.value = d["value"]
        return attribute
