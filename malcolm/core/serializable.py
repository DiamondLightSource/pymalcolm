import re
import logging
import json

from annotypes import TYPE_CHECKING, serialize_object as _serialize_object
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


def serialize_object(o):
    return _serialize_object(o, OrderedDict)


def serialize_hook(o):
    o = serialize_object(o)
    # Cheaper than subclass check...
    if o.__class__.__name__ == "Array":
        # Unwrap the array as it might be a list, tuple or numpy array
        o = o.seq
    if hasattr(o, "tolist"):
        # Numpy bools, numbers and arrays all have a tolist function
        return o.tolist()
    elif isinstance(o, Exception):
        # Exceptions should be stringified
        return stringify_error(o)
    elif isinstance(o, Enum):
        # Return value of enums
        return o.value
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



