from collections import OrderedDict

from malcolm.compat import base_string
from malcolm.core.meta import Meta
from malcolm.core.serializable import Serializable
from malcolm.core.monitorable import NO_VALIDATE
from malcolm.core.vmetas import VMeta
from malcolm.core.map import Map


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Meta):
    """An object containing a set of ScalarMeta objects"""

    endpoints = ["elements", "description", "tags", "required"]

    def __init__(self, description="", tags=None):
        super(MapMeta, self).__init__(description, tags)
        self.elements = Map()
        self.required = []

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarMeta or serialized dict"""
        emap = Map()
        for k, v in elements.items():
            assert isinstance(k, base_string), "Expected string, got %s" % (k,)
            if k != "typeid":
                emap[k] = self._cast(v, VMeta)
        self.set_endpoint(NO_VALIDATE, "elements", emap, notify)

    def set_required(self, required, notify=True):
        """Set the required string list"""
        self.set_endpoint([base_string], "required", required, notify)
