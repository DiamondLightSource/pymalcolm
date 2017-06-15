from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Map:1.0")
class Map(Serializable):

    def __init__(self, meta, d=None):
        self.endpoints = []
        self.meta = meta
        if d:
            self.update(d)

    def __setattr__(self, attr, val):
        if hasattr(self, "meta"):
            if attr not in self.meta.elements:
                raise AttributeError(
                    "%s is not a valid key for given meta" % attr)
            val = self.meta.elements[attr].validate(val)
            unordered_endpoints = self.endpoints + [attr]
            object.__setattr__(
                self, "endpoints",
                [x for x in self.meta.elements if x in unordered_endpoints])
        super(Map, self).__setattr__(attr, val)

    def __setitem__(self, key, val):
        try:
            setattr(self, key, val)
        except AttributeError:
            raise ValueError(key)

    def update(self, d):
        invalid = [k for k in d
                   if k not in self.meta.elements and k != "typeid"]
        if invalid:
            raise ValueError(
                "Keys %s from %s not in %s" % (
                    invalid, d, list(self.meta.elements)))
        for k in d:
            if k != "typeid":
                self[k] = d[k]

    def check_valid(self):
        invalid = [k for k in self.meta.required if k not in self.endpoints]
        if invalid:
            raise ValueError(
                "Keys %s from %s not set" % (invalid, self.meta.required))

    def __repr__(self):
        elements = ", ".join("%r: %r" % kv for kv in self.items())
        return "Map({%s})" % elements

    def clear(self):
        while self.endpoints:
            delattr(self, self.endpoints.pop())

    def keys(self):
        return self.endpoints[:]

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]

    def __eq__(self, rhs):
        return list(self.items()) == list(rhs.items())

    def __ne__(self, rhs):
        return not self == rhs
