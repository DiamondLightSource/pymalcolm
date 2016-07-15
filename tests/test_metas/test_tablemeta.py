import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import Mock

from malcolm.metas.tablemeta import TableMeta


class TestTableMetaInit(unittest.TestCase):

    def test_init(self):
        tm = TableMeta("name", "desc")
        self.assertEquals("name", tm.name)
        self.assertEquals("desc", tm.description)
        self.assertEquals("malcolm:core/TableMeta:1.0", tm.typeid)
        self.assertEquals([], tm.tags)
        self.assertEquals(True, tm.writeable)
        self.assertEquals("", tm.label)
        self.assertEquals([], tm.headings)

    def test_add_element(self):
        tm = TableMeta("name", "desc")
        am1 = Mock()
        am2 = Mock()
        tm.add_element(am1)
        tm.add_element(am2)

        expected = OrderedDict()
        expected[am1.name] = am1
        expected[am2.name] = am2
        self.assertEquals(expected, tm.elements)

    def test_add_duplicate_element_raises(self):
        tm = TableMeta("name", "desc")
        am1 = Mock()
        tm.add_element(am1)
        self.assertRaises(ValueError, tm.add_element, am1)

class TestTableMetaUpdates(unittest.TestCase):

    def test_set_writeable(self):
        tm = TableMeta("name", "desc")
        tm.on_changed = Mock(wrap=tm.on_changed)
        notify = Mock()
        writeable = Mock()
        tm.set_writeable(writeable, notify=notify)
        self.assertEquals(writeable, tm.writeable)
        tm.on_changed.assert_called_once_with(
            [["writeable"], writeable], notify)

    def test_set_label(self):
        tm = TableMeta("name", "desc")
        tm.on_changed = Mock(wrap=tm.on_changed)
        notify = Mock()
        label = Mock()
        tm.set_label(label, notify=notify)
        self.assertEquals(label, tm.label)
        tm.on_changed.assert_called_once_with(
            [["label"], label], notify)

    def test_set_headings(self):
        tm = TableMeta("name", "desc")
        tm.on_changed = Mock(wrap=tm.on_changed)
        notify = Mock()
        headings = Mock()
        tm.set_headings(headings, notify=notify)
        self.assertEquals(headings, tm.headings)
        tm.on_changed.assert_called_once_with(
            [["headings"], headings], notify)

    def test_notify_default_is_true(self):
        tm = TableMeta("name", "desc")
        value = Mock()
        tm.on_changed = Mock(wrap=tm.on_changed)
        tm.set_writeable(value)
        tm.set_headings(value)
        tm.set_label(value)
        calls = tm.on_changed.call_args_list
        self.assertTrue(calls[0][0][1])
        self.assertTrue(calls[1][0][1])
        self.assertTrue(calls[2][0][1])

class TestTableMetaSerialization(unittest.TestCase):

    def test_to_dict(self):
        tm = TableMeta("name", "desc")
        tm.writeable = Mock(spec=[])
        tm.label = Mock(spec=[])
        tm.headings = Mock(spec=[])
        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/TableMeta:1.0"
        expected["elements"] = tm.elements
        expected["description"] = tm.description
        expected["tags"] = tm.tags
        expected["writeable"] = tm.writeable
        expected["label"] = tm.label
        expected["headings"] = tm.headings
        self.assertEqual(expected, tm.to_dict())

    def test_from_dict(self):
        e1_mock = Mock()
        e2_mock = Mock()
        d = {"typeid":"malcolm:core/TableMeta:1.0",
                "elements":{"e1":e1_mock, "e2":e2_mock},
                "description":"desc",
                "tags":["tag"],
                "writeable":False,
                "label":"label",
                "headings":["heading_1", "heading_2"]}
        tm = TableMeta.from_dict("name", d)
        self.assertEquals("name", tm.name)
        self.assertEquals("desc", tm.description)
        self.assertEquals({"e1":e1_mock, "e2":e2_mock}, tm.elements)
        self.assertEquals(["tag"], tm.tags)
        self.assertEquals(False, tm.writeable)
        self.assertEquals("label", tm.label)
        self.assertEquals(["heading_1", "heading_2"], tm.headings)

class TestTableMetaValidation(unittest.TestCase):

    def test_validate(self):
        tm = TableMeta("name", "desc")
        tm.elements["e1"] = Mock()
        tm.elements["e2"] = Mock()
        tm.elements["e3"] = Mock()
        tm.elements["e4"] = Mock()
        tm.headings = ["column 1", "column 2", "column 3", "column 4"]
        d = {"e1":[1, 11, 21], "e2":[2, 12], "e3":[3, 13, 23], "e4":None}

        t = tm.validate(d)

        tm.elements["e1"].validate.assert_called_once_with([1, 11, 21])
        tm.elements["e2"].validate.assert_called_once_with([2, 12])
        tm.elements["e3"].validate.assert_called_once_with([3, 13, 23])
        tm.elements["e4"].validate.assert_called_once_with(None)
        self.assertEqual([1, 11, 21], t.e1)
        self.assertEqual([2, 12], t.e2)
        self.assertEqual([3, 13, 23], t.e3)
        self.assertEqual(None, t.e4)

    def test_validate_ignores_key_order(self):
        tm = TableMeta("name", "desc")
        tm.elements["e1"] = Mock()
        tm.elements["e2"] = Mock()
        d = OrderedDict()
        d["e2"] = [2]
        d["e1"] = [1]

        t = tm.validate(d)

        tm.elements["e1"].validate.assert_called_once_with([1])
        tm.elements["e2"].validate.assert_called_once_with([2])
        self.assertEqual([1], t.e1)
        self.assertEqual([2], t.e2)

    def test_validate_raises_on_bad_keys(self):
        tm = TableMeta("name", "desc")
        tm.elements["e1"] = Mock()
        d = {"e1":[1], "e2":[2]}
        self.assertRaises(ValueError, tm.validate, d)

        tm.elements["e2"] = Mock()
        tm.elements["e3"] = Mock()
        self.assertRaises(ValueError, tm.validate, d)

    def test_validate_raises_on_validation_failure(self):
        tm = TableMeta("name", "desc")
        tm.elements["e1"] = Mock()
        tm.elements["e2"] = Mock(validate=Mock(side_effect=ValueError))
        tm.elements["e3"] = Mock()

        d = {"e1":[0], "e2":[0], "e3":[0]}
        self.assertRaises(ValueError, tm.validate, d)

if __name__ == "__main__":
    unittest.main(verbosity=2)
