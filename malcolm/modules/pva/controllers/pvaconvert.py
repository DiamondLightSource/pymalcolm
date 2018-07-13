from annotypes import TYPE_CHECKING, Array
from enum import Enum
from p4p.wrapper import Type, Value
import numpy as np

from malcolm.compat import str_, long_

if TYPE_CHECKING:
    from typing import Dict, Tuple, List, Any

NOTHING = Value(Type([]))

# https://mdavidsaver.github.io/p4p/values.html
type_specifiers = {
    bool: '?',
    np.bool_: '?',
    np.int8: 'b',
    np.uint8: 'B',
    np.int16: 'h',
    np.uint16: 'S',
    np.int32: 'i',
    np.uint32: 'I',
    np.int64: 'l',
    int: 'l',
    long_: 'l',
    np.uint64: 'L',
    np.float32: 'f',
    np.float64: 'd',
    float: 'D',
    str: 's',
    str_: 's'
}


def convert_to_type_tuple_value(value):
    # type: (Any) -> Tuple[Any, Any]
    if isinstance(value, Array):
        if issubclass(value.typ, Enum):
            typ = str
        else:
            typ = value.typ
        ts = 'a' + type_specifiers[typ]
        value_for_set = value.seq
        # TODO: cope with arrays of objects
    elif isinstance(value, list):
        # TODO: remove this when scanpoint generator has types
        ts = 'av'
        value_for_set = [convert_to_type_tuple_value(v)[1] for v in value]
    elif isinstance(value, dict):
        typeid = value.get("typeid", "structure")
        fields = []
        value_for_set = {}
        for k, v in value.items():
            if k != "typeid":
                t, v_set = convert_to_type_tuple_value(v)
                fields.append((k, t))
                value_for_set[k] = v_set
        ts = ('S', typeid, fields)
    else:
        ts = type_specifiers[type(value)]
        value_for_set = value
    return ts, value_for_set


def convert_dict_to_value(d):
    # type: (Dict) -> Value
    if d is None:
        val = NOTHING
    else:
        (_, typeid, fields), value_for_set = convert_to_type_tuple_value(d)
        typ = Type(fields, typeid)
        val = Value(typ, value_for_set)
    return val


def update_path(value, path, update):
    # type: (Value, List[str], Any) -> None
    for p in path[:-1]:
        value = value[p]
    _, update = convert_to_type_tuple_value(update)
    value[path[-1]] = update


def pop_dict_wrapper(d, path):
    # type: (Dict, List[str]) -> (Dict, List[str])
    """Take dict with a single entry, putting it's value on path and
    returning its contents"""
    assert isinstance(d, dict) and len(d) == 1, \
        "Expected single element dict, got %s" % (d,)
    key, value = list(d.items())[0]
    path = path + [key]
    return value, path
