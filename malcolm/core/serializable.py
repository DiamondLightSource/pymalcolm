from collections import OrderedDict


class Serializable(object):
    """Mixin class for serializable objects"""

    # This will be set by subclasses calling cls.register_subclass()
    typeid = None

    # List of endpoint strings for to_dict()
    endpoints = None

    # dict mapping typeid name -> cls
    _subcls_lookup = {}

    def to_dict(self, **overrides):
        """
        Create a dictionary representation of object attributes

        Returns:
            dict: Serialised version of self
        """

        d = OrderedDict()
        d["typeid"] = self.typeid

        if self.endpoints is not None:
            for endpoint in self.endpoints:
                if endpoint in overrides:
                    value = overrides[endpoint]
                else:
                    value = getattr(self, endpoint)

                if hasattr(value, "to_dict"):
                    value = value.to_dict()

                d[endpoint] = value

        return d

    @classmethod
    def from_dict(cls, name, d):
        """
        Base method to create a serializable instance from a dictionary

        Args:
            d(dict): Class instance attributes to set

        Returns:
            Instance of subclass given in d
        """

        inst = cls()
        for k, v in d.items():
            # attribute_assignment e.g. [attribute, value]
            if k != "typeid":
                inst.update([[k], v])

        return inst

    @classmethod
    def deserialize(cls, name, d):
        """
        Look up subclass and call its from_dict function

        Args:
            d(dict): Class instance attributes to set

        Returns:
            Instance of subclass given in d
        """

        typeid = d["typeid"]
        subcls = cls.lookup_subclass(typeid)

        return subcls.from_dict(name, d)

    @classmethod
    def register_subclass(cls, typeid):
        """Register a subclass so from_dict() works

        Args:
            typeid (str): Type identifier for subclass
        """
        def decorator(subcls):
            cls._subcls_lookup[typeid] = subcls
            subcls.typeid = typeid
            return subcls
        return decorator

    @classmethod
    def lookup_subclass(cls, type_id):
        """
        Look up a class instance based on its type id
        Args:
            type_id: Specifier for subclass

        Returns:
            Class instance
        """

        return cls._subcls_lookup[type_id]

    def update(self, change):
        """
        Set a given attribute to a new value
        Args:
            change(tuple): Attribute path and value e.g. (value, 5)
        """

        if len(change[0]) != 1:
            raise ValueError(
                "Cannot handle multiple element path in change %s" % change)
        attribute = change[0][0]
        new_value = change[1]
        try:
            setter = getattr(self, "set_%s" % attribute)
        except AttributeError:
            raise ValueError(
                "Invalid update path specified in change %s" % change)
        setter(new_value)
