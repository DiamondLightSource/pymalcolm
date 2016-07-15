from collections import Counter

from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Map:1.0")
class Map(Serializable):

    def __init__(self, meta, d=None):
        self.meta = meta
        d = {} if d is None else d
        for key, value in d.items():
            if key in meta.elements:
                self.__setattr__(key, value)
            else:
                raise ValueError("%s is not a valid key for given meta" % key)

    @property
    def endpoints(self):
        return [e for e in self.meta.elements if hasattr(self, e)]

    def to_dict(self):
        overrides = {}
        for e in self.endpoints:
            a = getattr(self, e)
            if hasattr(a, "to_dict"):
                overrides[e] = a.to_dict()
        return super(Map, self).to_dict(**overrides)

    @classmethod
    def from_dict(cls, meta, d):
        m = cls(meta)
        for k, v in d.items():
            if k == "meta":
                continue
            try:
                # check if this is something that needs deserializing
                if "typeid" in v:
                    v = Serializable.deserialize(k, v)
            except TypeError:
                # not a dictionary - pass
                pass
            setattr(m, k, v)
        return m

    def __repr__(self):
        return self.to_dict().__repr__()

    def __eq__(self, rhs):
        if hasattr(rhs, "meta"):
            if self.meta.to_dict() != rhs.meta.to_dict():
                return False
        return Counter(self.items()) == Counter(rhs.items())

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def __setitem__(self, key, val):
        if key not in self.meta.elements:
            raise ValueError("%s is not a valid key for given meta" % key)
        setattr(self, key, val)

    def __getitem__(self, key):
        if key not in self.meta.elements or not hasattr(self, key):
            raise KeyError
        return getattr(self, key)

    def __contains__(self, key):
        return key in self.meta.elements and hasattr(self, key)

    def __len__(self):
        return len([e for e in self.meta.elements if hasattr(self, e)])

    def __iter__(self):
        for e in self.meta.elements:
            if hasattr(self, e):
                yield e

    def update(self, d):
        if not set(d).issubset(self.meta.elements):
            raise ValueError("%s contains invalid keys for given meta" % d)
        for k in d:
            setattr(self, k, d[k])

    def clear(self):
        for e in self.meta.elements:
            if hasattr(self, e):
                delattr(self, e)

    def keys(self):
        return [e for e in self.meta.elements if hasattr(self, e)]

    def values(self):
        return [getattr(self, e)
                for e in self.meta.elements if hasattr(self, e)]

    def items(self):
        return [(e, getattr(self, e))
                for e in self.meta.elements if hasattr(self, e)]

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        else:
            if key not in self.meta.elements:
                raise ValueError("%s is not a valid key for given meta" % key)
            self[key] = default
            return default
