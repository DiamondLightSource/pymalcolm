import re
import logging
import json

from annotypes import WithCallTypes, TypeVar, Any, TYPE_CHECKING, Array
from enum import Enum

from malcolm.compat import OrderedDict
from .errors import FieldError
if TYPE_CHECKING:
    from typing import Type, Union, Sequence

# Create a module level logger
log = logging.getLogger(__name__)

CAMEL_RE = re.compile(r"[a-z][a-z0-9]*([A-Z][a-z0-9]*)*$")


def stringify_error(e):
    # type: (Exception) -> str
    return "%s: %s" % (type(e).__name__, str(e))


def json_encode(o, indent=None):
    s = json.dumps(o, default=serialize_hook, indent=indent)
    return s


def json_decode(s):
    try:
        o = json.loads(s, object_pairs_hook=OrderedDict)
        assert isinstance(o, OrderedDict), "didn't return OrderedDict"
        return o
    except Exception as e:
        raise ValueError("Error decoding JSON object (%s)" % str(e))


def serialize_hook(o):
    o = serialize_object(o)
    if isinstance(o, Array):
        # Unwrap the array as it might be a list, tuple or numpy array
        o = o.seq
    if hasattr(o, "tolist"):
        # Numpy bools, numbers and arrays all have a tolist function
        return o.tolist()
    elif isinstance(o, Exception):
        # Exceptions should be stringified
        return stringify_error(o)
    else:
        # Everything else should be serializable already
        return o


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
        elif isinstance(o, Enum):
            return o.value
        else:
            # Hope it's serializable!
            return o


T = TypeVar("T")


def deserialize_object(ob, type_check=None):
    # type: (Any, Union[Type[T], Sequence[Type[T]]]) -> T
    if isinstance(ob, dict):
        subclass = Serializable.lookup_subclass(ob)
        ob = subclass.from_dict(ob)
    if type_check is not None:
        assert isinstance(ob, type_check), \
            "Expected %s, got %r" % (type_check, type(ob))
    return ob


class Serializable(WithCallTypes):
    """Base class for serializable objects"""

    # This will be set by subclasses calling cls.register_subclass()
    typeid = None

    # dict mapping typeid name -> cls
    _subcls_lookup = {}

    __slots__ = []

    def __getitem__(self, item):
        """Dictionary access to attr data"""
        if item in self.call_types:
            try:
                return getattr(self, item)
            except (AttributeError, TypeError):
                raise KeyError(item)
        else:
            raise KeyError(item)

    def __iter__(self):
        return iter(self.call_types)

    def to_dict(self):
        # type: () -> OrderedDict
        """Create a dictionary representation of object attributes

        Returns:
            OrderedDict serialised version of self
        """

        d = OrderedDict()
        if self.typeid:
            d["typeid"] = self.typeid

        for k in self.call_types:
            # check_camel_case(k)
            d[k] = serialize_object(getattr(self, k))

        return d

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
        try:
            inst = cls(**filtered)
        except TypeError as e:
            raise TypeError("%s raised error: %s" % (cls.typeid, str(e)))
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
        try:
            typeid = d["typeid"]
        except KeyError:
            raise FieldError("typeid not present in keys %s" % list(d))

        subclass = cls._subcls_lookup.get(typeid, None)
        if not subclass:
            raise FieldError("'%s' not a valid typeid" % typeid)
        else:
            return subclass