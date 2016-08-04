from collections import OrderedDict

from malcolm.core.serializable import Serializable
from malcolm.core.monitorable import Monitorable


@Serializable.register_subclass("malcolm:core/Map:1.0")
class Map(OrderedDict, Monitorable):
    # real data stored as attributes
    # dictionary type view supported

    def __init__(self, meta=None, d=None):
        super(Map, self).__init__(self)
        self.meta = meta
        if d:
            self.update(d)

    @property
    def endpoints(self):
        if self.meta:
            return [e for e in self.meta.elements if e in self]
        else:
            return list(self)

    def get_endpoint(self, endpoint):
        return self[endpoint]

    def __setattr__(self, attr, val):
        if hasattr(self, "meta") and self.meta:
            self[attr] = val
        else:
            object.__setattr__(self, attr, val)

    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            raise AttributeError(key)

    def __setitem__(self, key, val):
        if self.meta:
            if key not in self.meta.elements:
                raise ValueError("%s is not a valid key for given meta" % key)
            val = self.meta.elements[key].validate(val)
        if hasattr(val, "set_parent"):
            val.set_parent(self, key)
        super(Map, self).__setitem__(key, val)

    def update(self, d):
        if self.meta:
            invalid = [k for k in d
                       if k not in self.meta.elements and k != "typeid"]
            if invalid:
                raise ValueError(
                    "Keys %s are not valid for this map" % (invalid,))
        for k in d:
            if k != "typeid":
                self[k] = d[k]

    def check_valid(self):
        for e in self.meta.required:
            if e not in self.endpoints:
                raise KeyError(e)

