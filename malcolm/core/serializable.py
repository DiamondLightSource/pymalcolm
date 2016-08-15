from collections import OrderedDict

import numpy as np


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
    elif isinstance(o, np.number):
        return o.tolist()
    elif isinstance(o, np.ndarray):
        assert len(o.shape) == 1, \
            "Expected 1d array, got {}".format(o.shape)
        return o.tolist()
    else:
        # Hope it's serializable!
        return o


def deserialize_object(ob, type_check=None):
    if isinstance(ob, dict):
        subclass = Serializable.lookup_subclass(ob)
        ob = subclass.from_dict(ob)
    if type_check is not None:
        assert isinstance(ob, type_check), \
            "Expected %s, got %r" % (type_check, ob)
    return ob


class Serializable(object):
    """Mixin class for serializable objects"""

    # This will be set by subclasses calling cls.register_subclass()
    typeid = None

    # List of endpoint strings for to_dict()
    endpoints = None

    # dict mapping typeid name -> cls
    _subcls_lookup = {}

    # instance dictionary of endpoint data
    _endpoint_data = None

    def __len__(self):
        if self.endpoints is None:
            return 0
        return len(self.endpoints)

    def __iter__(self):
        if self.endpoints is None:
            return iter(())
        return iter(self.endpoints)

    def __getitem__(self, item):
        """Dictionary access to endpoint data"""
        try:
            return self._endpoint_data[item]
        except (KeyError, TypeError):
            raise KeyError(item)

    def __getattr__(self, item):
        """Attr access to endpoint data, if not already in self"""
        try:
            return self._endpoint_data[item]
        except (KeyError, TypeError):
            raise AttributeError(item)

    def __setattr__(self, item, value):
        """Make sure we aren't shadowing an endpoint"""
        if item in self:
            raise AttributeError(
                "Setting attr %s would shadow an endpoint %s. Use a setter" %
                (item, list(self)))
        super(Serializable, self).__setattr__(item, value)

    def to_dict(self):
        """
        Create a dictionary representation of object attributes

        Returns:
            dict: Serialised version of self
        """

        d = OrderedDict()
        d["typeid"] = self.typeid

        for endpoint in self:
            value = self._endpoint_data[endpoint]
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
        inst = cls()
        inst.replace_endpoints(d)
        return inst

    def set_endpoint_data(self, name, value, **kwargs):
        # Called by subclass to set endpoint data
        assert name in self, \
            "Endpoint %r not defined for %r" % (name, self)
        if self._endpoint_data is None:
            self._endpoint_data = {}
        self._endpoint_data[name] = value

    def replace_endpoints(self, d):
        # Update the instance with any values in the dictionary that are known
        # endpoints
        done = []
        for endpoint in self:
            if endpoint in d:
                setter = getattr(self, "set_%s" % endpoint)
                setter(d[endpoint])
                done.append(endpoint)

        # For anything that is not a known endpoint it must be a typeid or a
        # new endpoint
        for k, v in d.items():
            if k not in done:
                if k == "typeid":
                    assert v == self.typeid, \
                        "Dict has typeid %s but %s has typeid %s" % \
                        (v, self, self.typeid)
                else:
                    raise ValueError(
                        "Unknown endpoint %s for %s" % (k, self))

    @classmethod
    def register_subclass(cls, typeid):
        """Register a subclass so from_dict() works

        Args:
            typeid (str): Type identifier for subclass
        """
        def decorator(subclass):
            cls._subcls_lookup[typeid] = subclass
            subclass.typeid = typeid
            return subclass
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
        subclass = cls._subcls_lookup[typeid]
        return subclass
