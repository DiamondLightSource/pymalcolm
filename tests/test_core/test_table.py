import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import Mock

from malcolm.core import Table
from malcolm.core.vmetas import NumberArrayMeta, StringArrayMeta


class TestTableInit(unittest.TestCase):
    def test_init(self):
        meta = Mock()
        s = StringArrayMeta()
        meta.elements = {"e1":s, "e2":s, "e3":s}
        t = Table(meta)
        self.assertEquals((), t.e1)
        self.assertEquals((), t.e2)
        self.assertEquals((), t.e3)
        self.assertEquals("malcolm:core/Table:1.0", t.typeid)

    def test_init_with_dict(self):
        meta = Mock()
        meta.elements = {"e1": NumberArrayMeta("int32"),
                         "e2": StringArrayMeta(),
                         "e3": StringArrayMeta()}
        d = {"e1":[0, 1], "e3":["value"]}
        t = Table(meta, d)
        self.assertEquals([0, 1], list(t.e1))
        self.assertEquals((), t.e2)
        self.assertEquals(("value",), t.e3)
        self.assertEquals("malcolm:core/Table:1.0", t.typeid)

    def test_init_with_none(self):
        meta = Mock()
        meta.elements = {"e1": StringArrayMeta()}
        t = Table(meta, None)
        self.assertEquals((), t.e1)
        self.assertEquals("malcolm:core/Table:1.0", t.typeid)


class TestTableRowOperations(unittest.TestCase):
    def setUp(self):
        meta = Mock()
        meta.elements = OrderedDict()
        meta.elements["e1"] = NumberArrayMeta("int32")
        meta.elements["e2"] = NumberArrayMeta("int32")
        meta.elements["e3"] = NumberArrayMeta("int32")
        self.t = Table(meta)
        self.t.e1 = [1]
        self.t.e2 = [2]
        self.t.e3 = [3]

    def test_row_access(self):
        self.assertEqual([1, 2, 3], self.t[0])

    def test_string_access(self):
        self.assertEqual(self.t.e1, self.t["e1"])
        self.assertEqual(self.t.e2, self.t["e2"])

    def test_string_setters(self):
        self.t["e2"] = [4]
        self.assertEqual(list(self.t.e2), [4])

    def test_row_access_index_error(self):
        with self.assertRaises(IndexError):
            self.t[1]
        self.t.e1 = [1, 11]
        self.t.e2 = [2, 12]
        self.t.e3 = [3, 13]
        self.t[1]
        with self.assertRaises(IndexError):
            self.t[2]

    def test_row_assignment(self):
        self.t[0] = [7, 8, 9]
        self.assertEqual([7], self.t.e1)
        self.assertEqual([8], self.t.e2)
        self.assertEqual([9], self.t.e3)

    def test_row_assignment_bad_row_raises(self):
        with self.assertRaises(ValueError):
            self.t[0] = [7, 8]
        self.assertEqual([1], self.t.e1)
        self.assertEqual([2], self.t.e2)
        self.assertEqual([3], self.t.e3)

    def test_row_assingment_index_error(self):
        with self.assertRaises(IndexError):
            self.t[1] = [7, 8, 9]

    def test_row_append(self):
        self.t.append([11, 12, 13])
        self.t.append([21, 22, 23])
        self.assertEquals([1, 11, 21], list(self.t.e1))
        self.assertEquals([2, 12, 22], list(self.t.e2))
        self.assertEquals([3, 13, 23], list(self.t.e3))

    def test_row_append_bad_row_raises(self):
        self.assertRaises(ValueError, self.t.append, [11, 12])
        self.assertRaises(ValueError, self.t.append, [11, 12, 13, 14])

    def test_bad_columns_raise(self):
        self.t.e1 = [1, 2]
        with self.assertRaises(AssertionError):
            self.t[0]
        with self.assertRaises(AssertionError):
            self.t[0] = [0, 0, 0]
        with self.assertRaises(AssertionError):
            self.t.append([0, 0, 0])


class TestTableMetaSerialization(unittest.TestCase):

    def setUp(self):
        meta = Mock()
        meta.elements = OrderedDict()
        meta.elements["e1"] = StringArrayMeta()
        meta.elements["e2"] = NumberArrayMeta("int32")
        meta.elements["e3"] = NumberArrayMeta("int32")
        self.meta = meta

    def test_to_dict(self):
        t = Table(self.meta)
        t.e1 = ["value"]
        t.e2 = [1, 2]
        t.e3 = [0]

        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/Table:1.0"
        expected["e1"] = ["value"]
        expected["e2"] = [1, 2]
        expected["e3"] = [0]
        actual = t.to_dict()
        # numpy compare gets in the way...
        for k, v in actual.items():
            if k != "typeid":
                actual[k] = list(v)
        self.assertEquals(expected, actual)

    def test_from_dict(self):
        d = {"e2":[0, 1, 2], "e1":["value"], "e3":[6, 7]}
        t = Table(self.meta, d)
        self.assertEqual(self.meta, t.meta)
        self.assertEqual([0, 1, 2], list(t.e2))
        self.assertEqual(("value",), t.e1)
        self.assertEqual([6, 7], list(t.e3))

    def test_dict_roundtrip(self):
        t = Table(self.meta)
        d = t.to_dict()
        d2 = d.copy()
        d2.pop("typeid")
        t2 = Table(self.meta, d2)
        self.assertEqual(d, t2.to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
