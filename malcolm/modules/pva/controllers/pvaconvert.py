from annotypes import TYPE_CHECKING, Array
from enum import Enum
from p4p import Type, Value
import numpy as np

from malcolm.compat import str_, long_, OrderedDict

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
    str_: 's',
})


try:
    # Python2
    type_specifiers[unicode] = 's'
except NameError:
    # Python3
    pass


def convert_to_type_tuple_value(value):
    # type: (Any) -> Tuple[Any, Any]
    if isinstance(value, Array):
        if issubclass(value.typ, Enum):
            typ = str
            value_for_set = [x.value for x in value.seq]
        else:
            typ = value.typ
            value_for_set = value.seq
        spec = 'a' + type_specifiers[typ]
        # TODO: cope with arrays of objects
    elif isinstance(value, np.ndarray):
        assert len(value.shape) == 1, \
            "Expected 1d array, got {}".format(value.shape)
        spec = 'a' + type_specifiers[value.dtype.type]
        value_for_set = value
    elif isinstance(value, list):
        specs = set()
        for v in value:
            t, _ = convert_to_type_tuple_value(v)
            if isinstance(t, tuple):
                t = 'av'
            specs.add(t)
        # TODO: remove this when scanpoint generator has types
        if len(specs) == 1:
            spec = specs.pop()
            if not spec.startswith("a"):
                spec = 'a%s' % spec
        else:
            spec = 'av'
        if spec == 'av':
            value_for_set = []
            for v in value:
                if isinstance(v, dict):
                    # Dict structures need to be turned into Values so they
                    # can give type information to the variant union
                    v = convert_dict_to_value(v)
                value_for_set.append(v)
        else:
            value_for_set = value
    elif isinstance(value, dict):
        typeid = value.get("typeid", "structure")
        fields = []
        value_for_set = {}
        for k, v in value.items():
            if k != "typeid":
                t, v_set = convert_to_type_tuple_value(v)
                fields.append((k, t))
                value_for_set[k] = v_set
        spec = ('S', typeid, fields)
    elif isinstance(value, Enum):
        spec = 's'
        value_for_set = value.value
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
#    elif spec[0] == "a":
        # Array of something with concrete type
        # typ = specifier_types[spec[1]]
        # return Array[typ](val)
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
        d[name] = convert_from_type_spec(spec, v[name])
    return d


def update_path(value, path, update):
    # type: (Value, List[str], Any) -> None
    for p in path[:-1]:
        value = value[p]
    _, update = convert_to_type_tuple_value(update)
    value[path[-1]] = update
