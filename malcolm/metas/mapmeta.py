from collections import OrderedDict

from malcolm.core.meta import Meta
from malcolm.metas.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable
from malcolm.compat import base_string


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Meta):
    """An object containing a set of ScalarMeta objects"""

    endpoints = ["elements", "description", "tags", "required"]

    def __init__(self, description="", tags=None):
        super(MapMeta, self).__init__(description, tags)
        self.elements = OrderedDict()
        self.required = []

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarMeta or serialized dict"""
        # Check correct type
        for name, element in elements.items():
            if isinstance(element, (dict, OrderedDict)):
                element = Serializable.from_dict(element)
                elements[name] = element
            assert isinstance(element, ScalarMeta), \
                "Expected ScalarMeta subclass, got %s" % (element,)
        self.set_endpoint("elements", elements, notify)

    def set_required(self, required, notify=True):
        """Set the required string list"""
        assert isinstance(required, list), \
            "Expected required to be a list, got %s" % (required,)
        for element_name in required:
            assert isinstance(element_name, base_string), \
                "Expected element_name to be string, got %s" % (element_name,)
        self.set_endpoint("required", required, notify)
