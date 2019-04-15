from annotypes import TYPE_CHECKING, Array
from enum import Enum
from p4p import Type, Value
import numpy as np

from malcolm.compat import str_, long_, OrderedDict
from malcolm.core import AlarmSeverity, AlarmStatus
from malcolm.core.models import NTTable

if TYPE_CHECKING:
    from typing import Dict, Tuple, List, Any

EMPTY = Value(Type([]))

# https://mdavidsaver.github.io/p4p/values.html
type_specifiers = {
    np.bool_: '?',
    np.int8: 'b',
    np.uint8: 'B',
    np.int16: 'h',
    np.uint16: 'H',
    np.int32: 'i',
    np.uint32: 'I',
    np.int64: 'l',
    np.uint64: 'L',
    np.float32: 'f',
    np.float64: 'd',
    str: 's',
}

# Make the reverse lookup
specifier_types = {v: k for k, v in type_specifiers.items()}

# Add some aliases
type_specifiers.update({
    bool: '?',
    int: 'l',
    long_: 'l',
    float: 'd',
})


try:
    # Python2
    type_specifiers[unicode] = 's'
except NameError:
    # Python3
    pass


def convert_to_type_tuple_value(value):
    # type: (Any) -> Tuple[Any, Any]
    # cheaper than a subclass check
    if value.__class__ is Array:
        if issubclass(value.typ, Enum):
            spec = "as"
            value_for_set = [x.value for x in value.seq]
        elif hasattr(value.typ, "to_dict"):
            # Array of objects
            spec = "av"
            value_for_set = [convert_dict_to_value(v) for v in value.seq]
        else:
            spec = 'a' + type_specifiers[value.typ]
            value_for_set = value.seq
    elif isinstance(value, np.ndarray):
        assert len(value.shape) == 1, \
            "Expected 1d array, got {}".format(value.shape)
        spec = 'a' + type_specifiers[value.dtype.type]
        value_for_set = value
    elif isinstance(value, list):
        # List of objects
        spec = "av"
        value_for_set = [convert_dict_to_value(v) for v in value]
    elif isinstance(value, dict) or hasattr(value, "to_dict"):
        try:
            typeid = value["typeid"]
        except KeyError:
            typeid = "structure"
        fields = []
        value_for_set = {}
        # Special case NTTable labels
        if typeid == NTTable.typeid:
            # Add labels for compatibility with epics normative types
            labels = []
            elements = value["meta"]["elements"]
            for column_name in elements:
                column_meta = elements[column_name]
                if column_meta["label"]:
                    labels.append(column_meta["label"])
                else:
                    labels.append(column_name)
            fields.append(("labels", "as"))
            value_for_set["labels"] = labels
        for k in value:
            if k != "typeid":
                t, v_set = convert_to_type_tuple_value(value[k])
                fields.append((k, t))
                value_for_set[k] = v_set
        spec = ('S', typeid, fields)
    elif isinstance(value, (AlarmSeverity, AlarmStatus)):
        spec = 'i'
        value_for_set = value.value
    elif isinstance(value, Enum):
        spec = 's'
        value_for_set = value.value
    elif isinstance(value, str_):
        spec = 's'
        value_for_set = value
    else:
        spec = type_specifiers[type(value)]
        value_for_set = value
    return spec, value_for_set


def convert_from_type_spec(spec, val):
    # type: (str, Any) -> Any
    if isinstance(spec, Type):
        # Structure
        return convert_value_to_dict(val)
    elif spec == "av":
        # Variant list of objects
        return [convert_value_to_dict(v) for v in val]
    #elif spec[0] == "a":
    #    # Array of something with concrete type
    #    # This currently fails because Array[np.float64] != Array[float]
    #    typ = specifier_types[spec[1]]
    #    return Array[typ](val)
    else:
        # Primitive
        return val


def convert_dict_to_value(d):
    # type: (Dict) -> Value
    if d is None:
        val = EMPTY
    else:
        (_, typeid, fields), value_for_set = convert_to_type_tuple_value(d)
        try:
            typ = Type(fields, typeid)
        except RuntimeError as e:
            raise RuntimeError(
                "%s when doing Type(%s, %s)" % (e, fields, typeid))
        val = Value(typ, value_for_set)
    return val


def convert_value_to_dict(v):
    # type: (Value) -> Dict
    d = OrderedDict()
    # Fill in typeid if set
    typeid = v.getID()
    if typeid != "structure":
        d["typeid"] = typeid
    # Fill in all the fields
    for name, spec in v.type().items():
        if typeid == NTTable.typeid and name == "labels":
            # NTTable might give us labels, ignore them
            continue
        d[name] = convert_from_type_spec(spec, v[name])
    return d


def update_path(value, path, update):
    # type: (Value, List[str], Any) -> None
    for p in path[:-1]:
        value = value[p]
    _, update = convert_to_type_tuple_value(update)
    value[path[-1]] = update
