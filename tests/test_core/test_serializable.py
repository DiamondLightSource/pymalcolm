from collections import OrderedDict
import unittest

import numpy as np
from annotypes import Anno, Array, Mapping, Union, Sequence, Any, \
    Serializable, deserialize_object

from malcolm.core.serializable import json_encode, serialize_object


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


class TestSerialization(unittest.TestCase):

    def test_json_numpy_array(self):
        s1 = DummySerializable(3, {}, np.array([3, 4]))
        assert json_encode(s1) == \
            '{"typeid": "foo:1.0", "boo": 3, "bar": {}, "NOT_CAMEL": [3, 4]}'

    def test_exception_serialize(self):
        s = json_encode(serialize_object({"message": ValueError("Bad result")}))
        assert s == '{"message": "ValueError: Bad result"}'
