from collections import Counter

from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Map:1.0")
class Map(Serializable):
    # real data stored as attributes
    # dictionary type view supported

    def __init__(self, meta, d=None):
        self.meta = meta
        d = {} if d is None else d
        for key, value in d.items():
            if key in meta.elements:
                setattr(self, key, value)
            else:
                raise ValueError("%s is not a valid key for given meta" % key)

    @property
    def endpoints(self):
        return [e for e in self.meta.elements if hasattr(self, e)]

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
        setattr(self, key, val)

    def __setattr__(self, attr, val):
        if hasattr(self, "meta"):
            if attr not in self.meta.elements:
                raise ValueError("%s is not a valid key for given meta" % attr)
            val = self.meta.elements[attr].validate(val)
        object.__setattr__(self, attr, val)

    def __getitem__(self, key):
        if key == "meta" or not hasattr(self, key):
            raise KeyError
        return getattr(self, key)

    def __contains__(self, key):
        return key != "meta" and hasattr(self, key)

    def __len__(self):
        return len(self.endpoints)

    def __iter__(self):
        for e in self.endpoints:
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
        return self.endpoints

    def values(self):
        return [getattr(self, e) for e in self.endpoints]

    def items(self):
        return [(e, getattr(self, e)) for e in self.endpoints]

    @classmethod
    def from_dict(cls, d, meta):
        d.pop("typeid")
        return cls(meta, d)
