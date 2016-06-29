from collections import OrderedDict

from malcolm.core.loggable import Loggable


class Serializable(Loggable):
    """Base class for serializable objects that can
    propagate changes to a parent"""

    # This will be set by subclasses calling cls.register()
    typeid = None
    # dict mapping typeid name -> (cls, args)
    _subcls_lookup = {}
    # dict mapping (cls, args) -> typeid
    _typeid_lookup = {}

    def __init__(self, name, *args):
        super(Serializable, self).__init__(logger_name=name)
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
            subcls (AttributeMeta): AttributeMeta subclass to register
            typeid (str): Type identifier for subclass
            *args: Additional arguments to be registered
        """
        def decorator(subcls):
            cls._subcls_lookup[typeid] = (subcls, args)
            cls._typeid_lookup[(subcls, args)] = typeid
            return subcls
        return decorator

    def set_parent(self, parent):
        """Sets the parent for changes to be propagated to"""
        self._logger_name = "%s.%s" % (parent.name, self.name)
        self.parent = parent

    def on_changed(self, change, notify=True):
        """Propagate change to parent, adding self.name to paths.

        Args:
            change: [[path], value] pair for changed values
        """
        if self.parent is None:
            return
        path = change[0]
        path.insert(0, self.name)
        self.parent.on_changed(change, notify)

    def update(self, change):
        raise NotImplementedError(
            "Abstract update function must be implemented in child classes")
