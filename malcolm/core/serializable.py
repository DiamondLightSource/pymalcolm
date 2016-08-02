from collections import OrderedDict


def serialize_object(o):
    if hasattr(o, "to_dict"):
        # This will do all the sub layers for us
        return o.to_dict()
    elif isinstance(o, (dict, OrderedDict)):
        # Need to recurse down
        d = OrderedDict()
        for k, v in o.items():
            d[k] = serialize_object(v)
        return d
    else:
        # Hope it's serializable!
        return o


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
                d[endpoint] = serialize_object(value)

        return d

    @classmethod
    def from_dict(cls, d):
        """
        Base method to create a serializable instance from a dictionary

        Args:
            d(dict): Class instance attributes to set

        Returns:
            Instance of subclass given in d
        """
        subcls = cls.lookup_subclass(d)
        inst = subcls()

        # Update the instance with any values in the dictionary that are known
        # endpoints
        if inst.endpoints:
            updates = [e for e in inst.endpoints if e in d]
            for endpoint in updates:
                setter = getattr(inst, "set_%s" % endpoint)
                setter(d.pop(endpoint))

        # For anything that is not a known endpoint it must be a typeid or a
        # new endpoint
        for k, v in d.items():
            if k == "typeid":
                assert v == inst.typeid, \
                    "Dict has typeid %s but Class has %s" % (v, inst.typeid)
            else:
                self.new_endpoint(k, v)
        return inst

    def new_endpoint(self, endpoint, value):
        raise NotImplementedError(
            "Setting new endpoint %s not implemented" % (endpoint,))

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
    def lookup_subclass(cls, d):
        """
        Look up a class based on a serialized dictionary containing a typeid

        Args:
            d (dict): Dictionary with key "typeid"

        Returns:
            Serializable subclass
        """
        typeid = d["typeid"]
        subcls = cls._subcls_lookup[typeid]
        return subcls

