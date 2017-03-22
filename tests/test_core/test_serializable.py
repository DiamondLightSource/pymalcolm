import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict
import unittest

from malcolm.core.serializable import Serializable, deserialize_object
from malcolm.vmetas.builtin.stringmeta import StringMeta

class TestSerialization(unittest.TestCase):

    @Serializable.register_subclass("foo:1.0")
    class DummySerializable(Serializable):
        endpoints = ["boo", "bar", "NOT_CAMEL"]

        def __init__(self, boo, bar, NOT_CAMEL):
            self.boo = self.set_boo(boo)
            self.bar = self.set_bar(bar)
            self.NOT_CAMEL = self.set_NOT_CAMEL(NOT_CAMEL)

        def set_boo(self, boo):
            return self.set_endpoint_data("boo", boo)

        def set_bar(self, bar):
            return self.set_endpoint_data("bar", bar)

        def set_NOT_CAMEL(self, c):
            return self.set_endpoint_data("NOT_CAMEL", c)

    @Serializable.register_subclass("empty:1.0")
    class EmptySerializable(Serializable):
        pass

    def test_to_dict(self):
        d = {'a':42, 'b':42}
        l = [42, 42]
        s = TestSerialization.DummySerializable(3, d, l)
        expected = OrderedDict(typeid="foo:1.0")
        expected["boo"] = 3
        expected["bar"] = d
        expected["NOT_CAMEL"] = l
        assert expected == s.to_dict()

        n = TestSerialization.DummySerializable.from_dict(expected)
        self.assertEqual(n.to_dict(), expected)

    def test_deserialize(self):
        a = TestSerialization.EmptySerializable()
        d = a.to_dict()
        b = deserialize_object(d)
        assert a == b

    def test_to_dict_children(self):
        a = StringMeta()
        b = TestSerialization.EmptySerializable()
        s = TestSerialization.DummySerializable(a, b, 0)
        expected = OrderedDict(typeid="foo:1.0")
        expected["boo"] = a
        expected["bar"] = b
        expected["NOT_CAMEL"] = 0

        assert expected == s.to_dict()

        n = TestSerialization.DummySerializable.from_dict(expected)
        assert n.to_dict() == expected

    def test_eq_etc(self):
        s1 = TestSerialization.DummySerializable(3, 3, 3)
        s2 = TestSerialization.DummySerializable(3, 3, 3)
        assert s1 == s2

        assert s1.__repr__() == \
            '{"typeid": "foo:1.0", "boo": 3, "bar": 3, "NOT_CAMEL": 3}'

        with self.assertRaises(KeyError):
            x = s1["boo2"]
        with self.assertRaises(KeyError):
            del s2.boo
            x = s2["boo"]

        assert len(s1) == 3
        s3 = TestSerialization.EmptySerializable()
        assert len(s3) == 0
        for endpoints in s3:
            assert False, "unexpected iteration over EmptySerializable"

        endpoints = []
        for endpoint in s1:
            endpoints.append(endpoint)
        assert endpoints == ["boo", "bar", "NOT_CAMEL"]

if __name__ == "__main__":
    unittest.main(verbosity=2)
