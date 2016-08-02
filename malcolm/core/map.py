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
                self[key] = value
            else:
                raise ValueError("%s is not a valid key for given meta" % key)

    @property
    def endpoints(self):
        return [e for e in self.meta.elements if hasattr(self, e)]

    def __repr__(self):
        return self.to_dict().__repr__()

    def __setattr__(self, attr, val):
        if hasattr(self, "meta"):
            self[attr] = val
        else:
            object.__setattr__(self, attr, val)

    def __setitem__(self, key, val):
        if key not in self.meta.elements:
            raise ValueError("%s is not a valid key for given meta" % key)
        val = self.meta.elements[key].validate(val)
        object.__setattr__(self, key, val)

    def __getitem__(self, key):
        if key in self.endpoints:
            return getattr(self, key)
        else:
            raise KeyError

    def __contains__(self, key):
        return key in self.endpoints

    def __len__(self):
        return len(self.endpoints)

    def __iter__(self):
        for e in self.endpoints:
            yield e

    def update(self, d):
        if not set(d).issubset(self.meta.elements):
            raise ValueError("%s contains invalid keys for given meta" % d)
        for k in d:
            self[k] = d[k]

    def clear(self):
        for e in self.meta.elements:
            if hasattr(self, e):
                delattr(self, e)

    def keys(self):
        return self.endpoints

    def values(self):
        return [self[e] for e in self.endpoints]

    def items(self):
        return [(e, self[e]) for e in self.endpoints]

    def check_valid(self):
        for e in self.meta.required:
            if e not in self.endpoints:
                raise KeyError(e)

    def __eq__(self, rhs):
        if isinstance(rhs, dict):
            # compare to dict
            d = self.to_dict()
            d.pop("typeid")
            return d == rhs
        return self.to_dict() == rhs.to_dict()

    def __ne__(self, rhs):
        return not self == rhs
