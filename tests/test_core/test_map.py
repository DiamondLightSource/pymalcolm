import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import MagicMock, Mock

from malcolm.core import Map, Serializable
from malcolm.core.vmetas import NumberMeta, StringMeta
from malcolm.core.meta import Meta
from malcolm.core.mapmeta import MapMeta
from malcolm.core.elementmap import ElementMap


class TestMap(unittest.TestCase):

    def setUp(self):
        n = NumberMeta(description='a number')
        s = StringMeta(description="a string")
        self.meta = MapMeta()
        self.meta.set_elements(ElementMap({"a": s, "b": s}))
        self.meta.set_required(["a"])
        self.nmeta = MapMeta()
        self.nmeta.set_elements(ElementMap({"a": n, "b": n}))
        self.nmeta.set_required(["a"])

    def test_init(self):
        b_mock = MagicMock()
        m = Map(self.meta, {"a":"test", "b":b_mock})
        self.assertEqual(self.meta, m.meta)
        self.assertEqual("test", m.a)
        self.assertIs(str(b_mock), m.b)
        self.assertEqual("malcolm:core/Map:1.0", m.typeid)

    def test_init_raises_on_bad_key(self):
        with self.assertRaises(ValueError):
            m = Map(self.meta, {"bad_key":MagicMock()})

    def test_empty_init(self):
        m = Map(self.meta, None)
        self.assertEqual(self.meta, m.meta)
        with self.assertRaises(AttributeError):
            m.a

    def test_to_dict(self):
        a_mock = MagicMock()
        s = StringMeta(description="a string")
        meta = Meta()
        meta.elements = OrderedDict()
        meta.elements["b"] = s
        meta.elements["c"] = s
        meta.elements["d"] = NumberMeta("int32")
        meta.elements["e"] = s
        m = Map(meta, {"b":"test", "d":123, "e":"e"})

        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/Map:1.0"
        expected["b"] = "test"
        expected["d"] = 123
        expected["e"] = "e"
        self.assertEquals(expected, m.to_dict())

    def test_from_dict(self):
        map_meta = MagicMock()
        map_meta.elements = {"a": Mock(), "b": Mock(), "c": Mock()}
        map_meta.elements["a"].validate.return_value = 124
        map_meta.elements["b"].validate.return_value = "Something"
        map_meta.required = ["a"]

        d = {"a":123, "b":{"typeid":"mock_typeid"}}
        m = Map(map_meta, d)
        self.assertEquals(124, m.a)
        self.assertEquals("Something", m.b)

    def test_equals_maps(self):
        self.meta.to_dict = MagicMock()
        m1 = Map(self.meta, {"a":"test"})
        m2 = Map(self.meta, {"a":"test2"})
        self.assertFalse(m1 == m2)
        self.assertTrue(m1 != m2)
        m2.a = "test"
        self.assertTrue(m1 == m2)
        self.assertFalse(m1 != m2)

        m2 = Map(self.meta, {"a":"test", "b":"test"})
        self.assertFalse(m1 == m2)
        m1["b"] = "test"
        self.assertTrue(m1 == m2)

        s = StringMeta(description="a string")
        meta2 = Meta()
        meta2.elements = {"a":s, "b":s}
        meta2.required = ["a"]
        meta2.to_dict = self.meta.to_dict
        m2 = Map(meta2, {"a":"test", "b":"test"})
        self.assertTrue(m1 == m2)

    def test_equals_dicts(self):
        m = Map(self.meta, {"a":"test"})
        d = {"a":"test"}
        self.assertTrue(m == d)
        self.assertFalse(m != d)

        m["b"] = "test"
        self.assertFalse(m == d)
        self.assertTrue(m != d)

        d["b"] = "test2"
        self.assertFalse(m == d)
        self.assertTrue(m != d)

        d["b"] = "test"
        self.assertTrue(m == d)
        self.assertFalse(m != d)

    def test_contains(self):
        m = Map(self.meta, {"a":"test"})
        self.assertTrue("a" in m)
        self.assertFalse("b" in m)
        self.assertFalse("__init__" in m)

    def test_get_item(self):
        m = Map(self.meta, {"a":"test"})
        self.assertEqual("test", m["a"])
        m.a = "test_2"
        self.assertEqual("test_2", m["a"])

    def test_get_item_raises_if_no_key(self):
        m = Map(self.meta, {"a":"test"})
        with self.assertRaises(KeyError):
            m["b"]

    def test_get_item_fails_if_non_key(self):
        m = Map(self.meta)
        with self.assertRaises(KeyError):
            m["__init__"]

    def test_set_item(self):
        m = Map(self.meta, {"a":1})
        a_mock = MagicMock()
        b_mock = MagicMock()
        m["a"] = a_mock
        m["b"] = b_mock
        self.assertEqual(str(a_mock), m.a)
        self.assertEqual(str(b_mock), m.b)

    def test_set_item_raises_invalid_key(self):
        m = Map(self.meta)
        with self.assertRaises(ValueError):
            m["c"] = MagicMock()

    def test_len(self):
        m = Map(self.meta)
        self.assertEqual(0, len(m))
        m.a = 1
        self.assertEqual(1, len(m))
        m.b = 1
        self.assertEqual(2, len(m))

    def test_iter(self):
        m = Map(self.meta, {"a":"x", "b":"y"})
        self.assertEqual({"a", "b"}, {x for x in m})

    def test_update(self):
        m = Map(self.nmeta, {"a":1})
        d = {"a":2, "b":2}
        m.update(d)
        self.assertEqual(2, m.a)
        self.assertEqual(2, m.b)

    def test_update_raises_on_invalid_key(self):
        m = Map(self.nmeta, {"a":1})
        d = {"a":2, "b":2, "c":2}
        with self.assertRaises(ValueError):
            m.update(d)
        self.assertEqual(1, m.a)
        with self.assertRaises(AttributeError):
            m.b
        with self.assertRaises(AttributeError):
            m.c

    def test_clear(self):
        m = Map(self.nmeta, {"a":1})
        m.clear()
        with self.assertRaises(AttributeError):
            m.a

    def test_keys(self):
        m = Map(self.nmeta, {"a": 1})
        self.assertEqual(["a"], list(m.keys()))
        m.b = 1
        self.assertEqual({"a", "b"}, set(m.keys()))

    def test_values(self):
        m = Map(self.nmeta, {"a":1})
        self.assertEqual([1], list(m.values()))
        m.b = 2
        self.assertEqual({1, 2}, set(m.values()))

    def test_items(self):
        m = Map(self.nmeta, {"b":2})
        self.assertEqual([("b", 2)], list(m.items()))
        m.a = 1
        self.assertEqual({("a", 1), ("b", 2)}, set(m.items()))

    def test_repr(self):
        m = Map(self.nmeta, {"b": 44})
        r = repr(m)
        self.assertEqual(r, "Map({'b': 44.0})")

if __name__ == "__main__":
    unittest.main(verbosity=2)
