from collections import OrderedDict
import unittest

import numpy as np
from annotypes import Anno, Array, Mapping, Union, Sequence, Any

from malcolm.core.serializable import Serializable, deserialize_object, \
    json_encode, serialize_object
from malcolm.core.models import StringMeta


with Anno("A Boo"):
    ABoo = int
with Anno("A Bar"):
    ABar = Mapping[str, Any]
with Anno("A Not Camel"):
    ANotCamel = Array[int]
UNotCamel = Union[ANotCamel, Sequence[int]]


@Serializable.register_subclass("foo:1.0")
class DummySerializable(Serializable):
    boo = None
    bar = None
    NOT_CAMEL = None

    def __init__(self, boo, bar, NOT_CAMEL):
        # type: (ABoo, ABar, UNotCamel) -> None
        self.set_boo(boo)
        self.set_bar(bar)
        self.set_not(NOT_CAMEL)

    def set_boo(self, boo):
        self.boo = boo

    def set_bar(self, bar):
        d = OrderedDict()
        for k, v in bar.items():
            if k != "typeid":
                d[k] = deserialize_object(v)
        self.bar = d

    def set_not(self, c):
        self.NOT_CAMEL = ANotCamel(c)


@Serializable.register_subclass("empty:1.0")
class EmptySerializable(Serializable):
    pass


class TestSerialization(unittest.TestCase):

    def test_to_dict(self):
        d = {'a': 42, 'b': 42}
        l = [42, 42]
        s = DummySerializable(3, d, l)
        expected = OrderedDict(typeid="foo:1.0")
        expected["boo"] = 3
        expected["bar"] = d
        expected["NOT_CAMEL"] = l
        assert expected == s.to_dict()

        n = DummySerializable.from_dict(expected)
        assert n.to_dict() == expected

    def test_deserialize(self):
        a = EmptySerializable()
        d = a.to_dict()
        b = deserialize_object(d)
        assert a.to_dict() == b.to_dict()

    def test_to_dict_children(self):
        children = OrderedDict()
        children["a"] = StringMeta().to_dict()
        children["b"] = EmptySerializable().to_dict()
        s = DummySerializable(3, children, [])
        expected = OrderedDict(typeid="foo:1.0")
        expected["boo"] = 3
        expected["bar"] = children
        expected["NOT_CAMEL"] = []

        assert expected == s.to_dict()

        n = DummySerializable.from_dict(expected)
        assert n.to_dict() == expected

    def test_json_numpy_array(self):
        s1 = DummySerializable(3, {}, np.array([3, 4]))
        assert json_encode(s1) == \
            '{"typeid": "foo:1.0", "boo": 3, "bar": {}, "NOT_CAMEL": [3, 4]}'

    def test_exception_serialize(self):
        s = json_encode(serialize_object({"message": ValueError("Bad result")}))
        assert s == '{"message": "ValueError: Bad result"}'
