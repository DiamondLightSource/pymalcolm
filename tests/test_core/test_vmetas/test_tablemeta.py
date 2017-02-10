import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import Mock

from malcolm.core.vmetas import StringArrayMeta, TableMeta
from malcolm.core import Table
from malcolm.core.tableelementmap import TableElementMap


class TestTableMetaInit(unittest.TestCase):

    def test_init(self):
        tm = TableMeta("desc")
        self.assertEquals("desc", tm.description)
        self.assertEquals("malcolm:core/TableMeta:1.0", tm.typeid)
        self.assertEquals((), tm.tags)
        self.assertEquals(False, tm.writeable)
        self.assertEquals("", tm.label)


class TestTableMetaSetters(unittest.TestCase):
    def setUp(self):
        tm = TableMeta("desc")
        tm.process = Mock()
        self.tm = tm

    def test_set_elements(self):
        tm = self.tm
        elements = OrderedDict()
        elements["col1"]=StringArrayMeta()
        elements["col2"]=StringArrayMeta()
        elements = TableElementMap(elements)
        tm.set_elements(elements)
        self.assertEqual(elements, tm.elements)
        tm.process.report_changes.assert_called_once_with(
            [["elements"], elements.to_dict()])

    def test_set_elements_from_serialized(self):
        tm = self.tm
        elements = OrderedDict()
        elements["col1"]=StringArrayMeta()
        elements["col2"]=StringArrayMeta()
        elements = TableElementMap(elements)
        serialized = elements.to_dict()
        tm.set_elements(serialized)
        self.assertEqual(serialized, tm.elements.to_dict())


class TestTableMetaSerialization(unittest.TestCase):

    def setUp(self):
        self.sam = StringArrayMeta()
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/TableMeta:1.0"
        self.serialized["elements"] = TableElementMap(
            dict(c1=self.sam)).to_dict()
        self.serialized["description"] = "desc"
        self.serialized["tags"] = ()
        self.serialized["writeable"] = True
        self.serialized["label"] = "Name"

    def test_to_dict(self):
        tm = TableMeta("desc")
        tm.set_label("Name")
        tm.set_elements(TableElementMap(dict(c1=self.sam)))
        tm.set_writeable(True)
        self.assertEqual(tm.to_dict(), self.serialized)

    def test_from_dict(self):
        tm = TableMeta.from_dict(self.serialized)
        self.assertEquals(tm.description, "desc")
        self.assertEquals(len(tm.elements), 1)
        self.assertEquals(tm.elements["c1"].to_dict(), self.sam.to_dict())
        self.assertEquals(tm.tags, ())
        self.assertEquals(tm.writeable, True)
        self.assertEquals(tm.label, "Name")


class TestTableMetaValidation(unittest.TestCase):
    def setUp(self):
        self.tm = TableMeta("desc")
        self.tm.set_elements(TableElementMap(dict(c1=StringArrayMeta())))

    def test_validate_from_good_table(self):
        tm = self.tm
        t = Table(tm)
        t.c1 = ["me", "me3"]
        t_serialized = t.to_dict()
        t = tm.validate(t)
        self.assertEqual(t.to_dict(), t_serialized)

    def test_validate_from_serialized(self):
        tm = self.tm
        serialized = dict(
            typeid="anything",
            c1=("me", "me3")
        )
        t = tm.validate(serialized)
        self.assertEqual(t.endpoints, ["c1"])
        self.assertEqual(t.c1, serialized["c1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
