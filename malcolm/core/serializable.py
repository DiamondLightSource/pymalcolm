from collections import OrderedDict

from malcolm.core.loggable import Loggable


class Serializable(object):
    """Base class for serializable objects that can
    propagate changes to a parent"""

    # This will be set by subclasses calling cls.register()
    typeid = None
    # dict mapping typeid name -> (cls, args)
    _subcls_lookup = {}
    # dict mapping (cls, args) -> typeid
    _typeid_lookup = {}

    def __init__(self, name, *args):
        self.name = name
        self.typeid = self._typeid_lookup[(type(self), args)]
        self.parent = None

    def to_dict(self):
        d = OrderedDict()
        d["typeid"] = self.typeid
        return d

    @classmethod
    def from_dict(cls, name, d):
        typeid = d["typeid"]
        subcls, args = cls._subcls_lookup[typeid]
        assert subcls is not cls, \
            "Subclass %s did not redefine from_dict" % subcls
        deserialized = subcls.from_dict(name, d, *args)
        deserialized.typeid = typeid
        return deserialized

    @classmethod
    def register(cls, typeid, *args):
        """Register a subclass so from_dict() works

        Args:
            subcls (Serializable): Serializable subclass to register
            typeid (str): Type identifier for subclass
            *args: Additional arguments to be registered
        """
        def decorator(subcls):
            cls._subcls_lookup[typeid] = (subcls, args)
            cls._typeid_lookup[(subcls, args)] = typeid
            return subcls
        return decorator

    def update(self, change):
        raise NotImplementedError(
            "Abstract update function must be implemented in child classes")
