from malcolm.compat import str_
from .meta import Meta
from .serializable import Serializable, deserialize_object
from .stringarray import StringArray
from .vmeta import VMeta


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Meta):
    """An object containing a set of ScalarMeta objects"""

    endpoints = ["elements", "description", "tags", "writeable", "label",
                 "required"]

    def __init__(self, description="", tags=(), writeable=False, label="",
                 elements=None, required=()):
        super(MapMeta, self).__init__(description, tags, writeable, label)
        if elements is None:
            elements = {}
        self.elements = self.set_elements(elements)
        self.required = self.set_required(required)

    def set_elements(self, elements):
        """Set the elements dict from a serialized dict"""
        for k, v in elements.items():
            k = deserialize_object(k, str_)
            elements[k] = deserialize_object(v, VMeta)
        return self.set_endpoint_data("elements", elements)

    def set_required(self, required):
        """Set the required string list"""
        required = StringArray(deserialize_object(t, str_) for t in required)
        for r in required:
            assert r in self.elements, \
                "Expected one of %r, got %r" % (list(self.elements), r)
        return self.set_endpoint_data("required", required)

