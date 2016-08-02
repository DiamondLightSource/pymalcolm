from collections import OrderedDict

from malcolm.compat import base_string
from malcolm.core.meta import Meta
from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


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
        self.set_endpoint(
            {base_string: VMeta}, "elements", elements, notify)

    def set_required(self, required, notify=True):
        """Set the required string list"""
        self.set_endpoint([base_string], "required", required, notify)
