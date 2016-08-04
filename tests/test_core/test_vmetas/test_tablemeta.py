import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import Mock

from malcolm.core import StringArrayMeta, TableMeta, Table, Map


class TestTableMetaInit(unittest.TestCase):

    def test_init(self):
        tm = TableMeta("desc")
        self.assertEquals("desc", tm.description)
        self.assertEquals("malcolm:core/TableMeta:1.0", tm.typeid)
        self.assertEquals([], tm.tags)
        self.assertEquals(False, tm.writeable)
        self.assertEquals("", tm.label)
        self.assertEquals([], tm.headings)


class TestTableMetaSetters(unittest.TestCase):
    def setUp(self):
        tm = TableMeta("desc")
        tm.report_changes = Mock(wrap=tm.report_changes)
        self.tm = tm

    def test_set_elements(self):
        tm = self.tm
        elements = OrderedDict()
        elements["col1"]=StringArrayMeta()
        elements["col2"]=StringArrayMeta()
        tm.set_elements(elements)
        serialized = Map(None, elements).to_dict()
        self.assertEqual(elements, tm.elements)
        tm.report_changes.assert_called_once_with(
            [["elements"], serialized])

    def test_set_elements_from_serialized(self):
        tm = self.tm
        elements = OrderedDict()
        elements["col1"]=StringArrayMeta()
        elements["col2"]=StringArrayMeta()
        serialized = OrderedDict((k, v.to_dict()) for k, v in elements.items())
        tm.set_elements(serialized)
        self.assertEqual(len(elements), len(tm.elements))
        for name, e in tm.elements.items():
            self.assertEqual(e.to_dict(), elements[name].to_dict())

    def test_set_headings(self):
        tm = self.tm
        headings = ["boo", "foo"]
        tm.set_headings(headings)
        self.assertEquals(headings, tm.headings)
        tm.report_changes.assert_called_once_with([["headings"], headings])


class TestTableMetaSerialization(unittest.TestCase):

    def setUp(self):
        self.sam = StringArrayMeta()
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/TableMeta:1.0"
        self.serialized["elements"] = Map(None, dict(c1=self.sam)).to_dict()
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = True
        self.serialized["label"] = "Name"
        self.serialized["headings"] = ["col1"]

    def test_to_dict(self):
        tm = TableMeta("desc")
        tm.label = "Name"
        tm.set_elements(dict(c1=self.sam))
        tm.writeable = True
        tm.headings = ["col1"]
        self.assertEqual(tm.to_dict(), self.serialized)

    def test_from_dict(self):
        tm = TableMeta.from_dict(self.serialized)
        self.assertEquals(tm.description, "desc")
        self.assertEquals(len(tm.elements), 1)
        self.assertEquals(tm.elements["c1"].to_dict(), self.sam.to_dict())
        self.assertEquals(tm.tags, [])
        self.assertEquals(tm.writeable, True)
        self.assertEquals(tm.label, "Name")
        self.assertEquals(tm.headings, ["col1"])


class TestTableMetaValidation(unittest.TestCase):
    def setUp(self):
        self.tm = TableMeta("desc")
        self.tm.set_elements(dict(c1=StringArrayMeta()))

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
            c1=["me", "me3"]
        )
        t = tm.validate(serialized)
        self.assertEqual(t.endpoints, ["c1"])
        self.assertEqual(t.c1, serialized["c1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
