from malcolm.compat import str_
from malcolm.core.elementmap import ElementMap
from malcolm.core.meta import Meta
from malcolm.core.serializable import Serializable, deserialize_object
from malcolm.core.stringarray import StringArray


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Meta):
    """An object containing a set of ScalarMeta objects"""

    endpoints = ["elements", "description", "tags", "writeable", "label",
                 "required"]

    def __init__(self, description="", tags=None, writeable=False, label=""):
        super(MapMeta, self).__init__(description, tags, writeable, label)
        self.set_elements(ElementMap())
        self.set_required([])

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarMeta or serialized dict"""
        elements = deserialize_object(elements, ElementMap)
        self.set_endpoint_data("elements", elements, notify)

    def set_required(self, required, notify=True):
        """Set the required string list"""
        for r in required:
            assert r in self.elements, \
                "Expected one of %r, got %r" % (list(self.elements), r)
        required = StringArray(deserialize_object(t, str_) for t in required)
        self.set_endpoint_data("required", required, notify)

