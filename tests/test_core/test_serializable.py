from collections import OrderedDict
import unittest

from malcolm.core.serializable import Serializable, deserialize_object
from malcolm.modules.builtin.vmetas.stringmeta import StringMeta


@Serializable.register_subclass("foo:1.0")
class DummySerializable(Serializable):
    endpoints = ["boo", "bar", "NOT_CAMEL"]
    boo = None
    bar = None
    NOT_CAMEL = None

    def __init__(self, boo, bar, NOT_CAMEL):
        self.set_boo(boo)
        self.set_bar(bar)
        self.set_NOT_CAMEL(NOT_CAMEL)

    def set_boo(self, boo):
        self.boo = boo

    def set_bar(self, bar):
        self.bar = bar

    def set_NOT_CAMEL(self, c):
        self.NOT_CAMEL = c


@Serializable.register_subclass("empty:1.0")
class EmptySerializable(Serializable):
    pass


class TestSerialization(unittest.TestCase):

    def test_to_dict(self):
        d = {'a':42, 'b':42}
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
        assert a == b

    def test_to_dict_children(self):
        a = StringMeta()
        b = EmptySerializable()
        s = DummySerializable(a, b, 0)
        expected = OrderedDict(typeid="foo:1.0")
        expected["boo"] = a
        expected["bar"] = b
        expected["NOT_CAMEL"] = 0

        assert expected == s.to_dict()

        n = DummySerializable.from_dict(expected)
        assert n.to_dict() == expected

    def test_eq_etc(self):
        s1 = DummySerializable(3, "foo", 3)
        s2 = DummySerializable(3, "foo", 3)
        assert s1 == s2
        assert not s1 != s2

        assert s1.__repr__() == \
            "<DummySerializable boo=3 bar='foo' NOT_CAMEL=3>"

        with self.assertRaises(KeyError):
            x = s1["boo2"]

        s2.boo2 = "Anything"

        with self.assertRaises(KeyError):
            x = s2["boo2"]

        s2.endpoints = s2.endpoints + ["boo2"]
        assert s2["boo2"] == "Anything"

        with self.assertRaises(KeyError):
            delattr(s2, "boo2")
            x = s2["boo2"]

        assert len(s1) == 3
        s3 = EmptySerializable()
        assert len(s3) == 0
        for endpoints in s3:
            assert False, "unexpected iteration over EmptySerializable"

        endpoints = []
        for endpoint in s1:
            endpoints.append(endpoint)
        assert endpoints == ["boo", "bar", "NOT_CAMEL"]
