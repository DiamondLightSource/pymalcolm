import re
import logging
import json

import numpy as np

from malcolm.compat import OrderedDict

# Create a module level logger
log = logging.getLogger(__name__)

camel_re = re.compile(r"[a-z][a-z0-9]*([A-Z][a-z0-9]*)*")


def json_encode(o, indent=None):
    s = json.dumps(o, default=serialize_hook, indent=indent)
    return s


def json_decode(s):
    o = json.loads(s, object_pairs_hook=OrderedDict)
    return o


def serialize_hook(o):
    o = serialize_object(o)
    if isinstance(o, (np.number, np.bool_)):
        return o.tolist()
    elif isinstance(o, np.ndarray):
        assert len(o.shape) == 1, "Expected 1d array, got {}".format(o.shape)
        return o.tolist()
    else:
        return o


def check_camel_case(name):
    match = camel_re.match(name)
    if not match:
        log.warning("String %r is not camelCase", name)


def camel_to_title(name):
    """Takes a camelCaseFieldName and returns an Title Case Field Name

    Args:
        name (str): E.g. camelCaseFieldName

    Returns:
        str: Title Case converted name. E.g. Camel Case Field Name
    """
    split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)", name)
    ret = " ".join(split)
    ret = ret[0].upper() + ret[1:]
    return ret


def snake_to_camel(name):
    """Takes a snake_field_name and returns a camelCaseFieldName

    Args:
        name (str): E.g. snake_field_name or SNAKE_FIELD_NAME

    Returns:
        str: camelCase converted name. E.g. capsFieldName
    """
    ret = "".join(x.title() for x in name.split("_"))
    ret = ret[0].lower() + ret[1:]
    return ret


def serialize_object(o):
    try:
        # This will do all the sub layers for us
        return o.to_dict()
    except AttributeError:
        if isinstance(o, dict):
            # Need to recurse down
            d = OrderedDict()
            for k, v in o.items():
                d[k] = serialize_object(v)
            return d
        elif isinstance(o, list):
            # Need to recurse down
            return [serialize_object(x) for x in o]
        else:
            # Hope it's serializable!
            return o


def repr_object(o):
    if hasattr(o, "to_dict"):
        # This will do all the sub layers for us
        return repr(o)
    elif isinstance(o, dict):
        # Need to recurse down
        text = ", ".join("%r: %s" % (k, repr_object(v)) for k, v in o.items())
        return "{%s}" % text
    elif isinstance(o, list):
        # Need to recurse down
        text = ", ".join(repr_object(x) for x in o)
        return "[%s]" % text
    else:
        # Hope it's serializable!
        return repr(o)


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
    endpoints = ()

    # dict mapping typeid name -> cls
    _subcls_lookup = {}

    def __len__(self):
        return len(self.endpoints)

    def __iter__(self):
        return iter(self.endpoints)

    def __getitem__(self, item):
        """Dictionary access to endpoint data"""
        if item in self.endpoints:
            try:
                return getattr(self, item)
            except (AttributeError, TypeError):
                raise KeyError(item)
        else:
            raise KeyError(item)

    def to_dict(self):
        """Create a dictionary representation of object attributes

        Returns:
            OrderedDict serialised version of self
        """

        d = OrderedDict()
        d["typeid"] = self.typeid

        for endpoint in self.endpoints:
            check_camel_case(endpoint)
            d[endpoint] = serialize_object(getattr(self, endpoint))

        return d

    def __repr__(self):
        fields = [(endpoint, repr_object(getattr(self, endpoint)))
                  for endpoint in self.endpoints]
        fields = " ".join("%s=%s" % f for f in fields)
        s = "<%s %s>" % (self.__class__.__name__, fields)
        return s

    def __eq__(self, other):
        if hasattr(other, "to_dict"):
            return self.to_dict() == other.to_dict()
        else:
            return self.to_dict() == other

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        # This is not technically correct, but will do...
        # https://stackoverflow.com/a/1608888
        return id(self)

    @classmethod
    def from_dict(cls, d, ignore=()):
        """Create an instance from a serialized version of cls

        Args:
            d(dict): Endpoints of cls to set
            ignore(tuple): Keys to ignore

        Returns:
            Instance of this class
        """
        filtered = {}
        for k, v in d.items():
            if k == "typeid":
                assert v == cls.typeid, \
                    "Dict has typeid %s but %s has typeid %s" % \
                    (v, cls, cls.typeid)
            elif k not in ignore:
                filtered[k] = v

        inst = cls(**filtered)
        return inst

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
        """Look up a class based on a serialized dictionary containing a typeid

        Args:
            d (dict): Dictionary with key "typeid"

        Returns:
            Serializable subclass
        """
        typeid = d["typeid"]
        subclass = cls._subcls_lookup[typeid]
        return subclass
