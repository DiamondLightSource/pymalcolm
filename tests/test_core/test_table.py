import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import Mock

from malcolm.core.table import Table


class TestTableInit(unittest.TestCase):
    def test_init(self):
        meta = Mock()
        meta.elements = {"e1":Mock(), "e2":Mock(), "e3":Mock()}
        t = Table(meta)
        self.assertEquals([], t.e1)
        self.assertEquals([], t.e2)
        self.assertEquals([], t.e3)
        self.assertEquals("malcolm:core/Table:1.0", t.typeid)

    def test_init_with_dict(self):
        meta = Mock()
        meta.elements = {"e1":Mock(), "e2":Mock(), "e3":Mock()}
        d = {"e1":[0, 1], "e3":["value"]}
        t = Table(meta, d)
        self.assertEquals([0, 1], t.e1)
        self.assertEquals([], t.e2)
        self.assertEquals(["value"], t.e3)
        self.assertEquals("malcolm:core/Table:1.0", t.typeid)

    def test_init_with_none(self):
        meta = Mock()
        meta.elements = {"e1":Mock()}
        t = Table(meta, None)
        self.assertEquals([], t.e1)
        self.assertEquals("malcolm:core/Table:1.0", t.typeid)

class TestTableRowOperations(unittest.TestCase):
    def setUp(self):
        meta = Mock()
        meta.elements = OrderedDict()
        meta.elements["e1"] = Mock()
        meta.elements["e2"] = Mock()
        meta.elements["e3"] = Mock()
        self.t = Table(meta)
        self.t.e1.append(1)
        self.t.e2.append(2)
        self.t.e3.append(3)

    def test_row_access(self):
        self.assertEqual([1, 2, 3], self.t[0])

    def test_row_access_index_error(self):
        with self.assertRaises(IndexError):
            self.t[1]
        self.t.e1.append(11)
        self.t.e2.append(12)
        self.t.e3.append(13)
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
        self.assertEquals([1, 11, 21], self.t.e1)
        self.assertEquals([2, 12, 22], self.t.e2)
        self.assertEquals([3, 13, 23], self.t.e3)

    def test_row_append_bad_row_raises(self):
        self.assertRaises(ValueError, self.t.append, [11, 12])
        self.assertRaises(ValueError, self.t.append, [11, 12, 13, 14])

    def test_bad_columns_raise(self):
        self.t.e2.append(2)
        with self.assertRaises(AssertionError):
            self.t[0]
        with self.assertRaises(AssertionError):
            self.t[0] = [0, 0, 0]
        with self.assertRaises(AssertionError):
            self.t.append([0, 0, 0])

class TestTableMetaSerialization(unittest.TestCase):

    def setUp(self):
        self.meta = Mock()
        self.meta.elements = OrderedDict()
        self.meta.elements["e1"] = Mock()
        self.meta.elements["e2"] = Mock()
        self.meta.elements["e3"] = Mock()

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
        self.assertEquals(expected, t.to_dict())

    def test_from_dict(self):
        d = {"typeid":"malcolm:core/Table:1.0",
            "e1":[0, 1, 2], "e2":["value"], "e3":[6, 7]}
        t = Table.from_dict(self.meta, d)
        self.assertEqual(self.meta, t.meta)
        self.assertEqual([0, 1, 2], t.e1)
        self.assertEqual(["value"], t.e2)
        self.assertEqual([6, 7], t.e3)

    def test_dict_roundtrip(self):
        e1 = Mock()
        e2 = [1, 2, 3]
        e3 = [None]
        t = Table(self.meta)
        d = t.to_dict()
        t2 = Table.from_dict(self.meta, d)
        self.assertEqual(d, t2.to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
