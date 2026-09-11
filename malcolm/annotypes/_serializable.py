import inspect
import json

from ._array import Array
from ._calltypes import WithCallTypes
from ._typing import TypeVar, TYPE_CHECKING
from ._frozen_dict import FrozenOrderedDict

try:
    from enum import Enum
except ImportError:
    has_enum = False
else:
    has_enum = True

if TYPE_CHECKING:
    from typing import Type, Dict, Any, Union, List, Tuple


def stringify_error(e):
    # type: (Exception) -> str
    return "%s: %s" % (type(e).__name__, str(e))


def json_encode(o, indent=None):
    s = json.dumps(o, default=serialize_object, indent=indent)
    return s


def json_decode(s, dict_cls=FrozenOrderedDict):
    try:
        o = json.loads(s, object_pairs_hook=dict_cls)
        assert isinstance(o, dict_cls), "didn't return %s" % dict_cls.__name__
        return o
    except Exception as e:
        raise ValueError("Error decoding JSON object (%s)" % str(e))


def serialize_object(o, dict_cls=FrozenOrderedDict):
    # type: (Any, Type[dict]) -> Any
    # Is it a Serializable?
    to_dict = getattr(o, "to_dict", None)
    if to_dict is not None:
        return to_dict(dict_cls)

    # Is it a dict?
    if isinstance(o, dict):
        # Need to recurse down in case we have a serializable object in the
        # dict or somewhere further down the tree
        return dict_cls((k, serialize_object(v, dict_cls))
                        for k, v in o.items())

    # Is it an Array, list or numpy array?
    if o.__class__ is Array:
        # If we wrapped list, this will tell it what might be in it
        list_cls = o.typ
        # Unwrap the array as it might be a list, tuple or numpy array
        o = o.seq
    else:
        # Don't know what would be in a list, so give it something that will
        # require it to recurse
        list_cls = Serializable
    if isinstance(o, list):
        if inspect.isclass(list_cls) and (
            hasattr(list_cls, "to_dict") or
            isinstance(list_cls, Exception) or (
                has_enum and isinstance(list_cls, Enum))):
            recurse = True
        else:
            recurse = False
        if recurse:
            return [serialize_object(x) for x in o]
        else:
            return o
    elif hasattr(o, "tolist"):
        # Numpy bools, numbers and arrays all have a tolist function
        return o.tolist()
    elif isinstance(o, Exception):
        # Exceptions should be stringified
        return stringify_error(o)
    elif has_enum and isinstance(o, Enum):
        # Return value of enums
        return o.value
    else:
        # Everything else should be serializable already
        return o


T = TypeVar("T")


def deserialize_object(ob, type_check=None):
    # type: (Any, Union[Type[T], Tuple[Type[T], ...]]) -> T
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
    _subcls_lookup = {}  # type: Dict[str, Serializable]

    __slots__ = []  # type: List[str]

    def __getitem__(self, item):
        """Dictionary access to attr data"""
        if item in self.call_types:
            try:
                return getattr(self, item)
            except (AttributeError, TypeError):
                raise KeyError(item)
        elif item is "typeid" and self.typeid is not None:
            return self.typeid
        else:
            raise KeyError(item)

    def __iter__(self):
        return iter(self.call_types)

    def to_dict(self, dict_cls=FrozenOrderedDict):
        # type: (Type[dict]) -> Dict[str, Any]
        """Create a dictionary representation of object attributes

        Returns:
            OrderedDict serialised version of self
        """
        if self.typeid:
            keys = ["typeid"] + list(self.call_types)
        else:
            keys = self.call_types

        pairs = ((k, serialize_object(getattr(self, k), dict_cls))
                 for k in keys)
        d = dict_cls(pairs)
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

        Raises:
            TypeError: on bad typeid
        """
        try:
            typeid = d["typeid"]
        except KeyError:
            raise TypeError("typeid not present in keys %s" % list(d))

        subclass = cls._subcls_lookup.get(typeid, None)
        if not subclass:
            raise TypeError("'%s' not a valid typeid" % typeid)
        else:
            return subclass
