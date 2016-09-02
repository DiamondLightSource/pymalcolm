from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Map:1.0")
class Map(Serializable):

    def __init__(self, meta, d=None):
        self.endpoints = []
        self.meta = meta
        if d:
            self.update(d)

    def __setattr__(self, attr, val):
        if hasattr(self, "meta") and attr in self.meta.elements:
            self[attr] = val
        else:
            super(Map, self).__setattr__(attr, val)

    def __setitem__(self, key, val):
        if key not in self.meta.elements:
            raise ValueError("%s is not a valid key for given meta" % key)
        val = self.meta.elements[key].validate(val)
        self.endpoints = [
            k for k in self.meta.elements if k in list(self) + [key]]
        self.set_endpoint_data(key, val)

    def update(self, d):
        invalid = [k for k in d
                   if k not in self.meta.elements and k != "typeid"]
        if invalid:
            raise ValueError(
                "Keys %s not in %s" % (invalid, list(self.meta.elements)))
        for k in d:
            if k != "typeid":
                self[k] = d[k]

    def check_valid(self):
        for e in self.meta.required:
            if e not in self.endpoints:
                raise KeyError(e)

    def __repr__(self):
        elements = ", ".join("%r: %r" % kv for kv in self.items())
        return "Map({%s})" % elements

    def clear(self):
        self._endpoint_data = {}
        self.endpoints = []

    def keys(self):
        return self.endpoints

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    def __eq__(self, rhs):
        return list(self.items()) == list(rhs.items())

    def __ne__(self, rhs):
        return not self == rhs