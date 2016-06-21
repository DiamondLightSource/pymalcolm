from collections import OrderedDict

from malcolm.core.monitorable import Monitorable


class AttributeMeta(Monitorable):
    """Abstract base class for Meta objects"""

    # This will be set by subclasses calling cls.register_subclass()
    metaOf = None
    # dict mapping metaOf name -> (cls, args)
    _subcls_lookup = {}
    # dict mapping (cls, args) -> metaOf
    _metaOf_lookup = {}

    def __init__(self, name, description, *args):
        super(AttributeMeta, self).__init__(name=name)
        self.description = description
        self.metaOf = self._metaOf_lookup[(type(self), args)]

    def validate(self, value):
        """
        Abstract function to validate a given value

        Args:
            value(abstract): Value to validate
        """

        raise NotImplementedError(
            "Abstract validate function must be implemented in child classes")

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()
        d["description"] = self.description
        d["metaOf"] = self.metaOf

        return d

    @classmethod
    def register_subclass(cls, metaOf, *args):
        """Register a subclass so from_dict() works

        Args:
            subcls (AttributeMeta): AttributeMeta subclass to register
            metaOf (str): Like "malcolm:core/String:1.0"
            *args: Additional arguments to be registered
        """
        def decorator(subcls):
            cls._subcls_lookup[metaOf] = (subcls, args)
            cls._metaOf_lookup[(subcls, args)] = metaOf
            return subcls
        return decorator

    @classmethod
    def from_dict(cls, name, d):
        """Create a AttributeMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): AttributeMeta instance name
            d (dict): Something that self.to_dict() would create
        """
        metaOf = d["metaOf"]
        subcls, args = cls._subcls_lookup[metaOf]
        assert subcls is not cls, \
            "Subclass %s did not redefine from_dict" % subcls
        attribute_meta = subcls.from_dict(name, d, *args)
        attribute_meta.metaOf = metaOf
        return attribute_meta
