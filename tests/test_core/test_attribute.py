import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import Mock, patch

from malcolm.core.attribute import Attribute
from malcolm.core.scalarmeta import ScalarMeta


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self.meta = Mock()
        self.meta.name = "meta"

    def test_init(self):
        a = Attribute("test", self.meta)
        self.assertEquals("test", a.name)
        self.assertIs(self.meta, a.meta)
        self.assertIsNone(a.value)
        self.assertEquals("epics:nt/NTAttribute:1.0", a.typeid)

    def test_invalid_meta_name_raises(self):
        self.meta.name = "not_meta"
        with self.assertRaises(ValueError):
            a = Attribute("test", self.meta)

    def test_set_put_function(self):
        func = Mock()
        a = Attribute("test", self.meta)
        a.set_put_function(func)
        self.assertIs(func, a.put_func)

    def test_set_value(self):
        value = "test_value"
        a = Attribute("test", self.meta)
        a.on_changed = Mock(a.on_changed)
        a.set_value(value)
        self.assertEquals("test_value", a.value)
        a.on_changed.assert_called_once_with([['value'], value])

    def test_put(self):
        func = Mock()
        value = "test_value"
        a = Attribute("test", self.meta)
        a.set_put_function(func)
        a.put(value)
        func.assert_called_once_with(value)

    def test_to_dict(self):
        self.meta.to_dict = Mock(return_value = {"test_meta":"dict"})
        expected = OrderedDict()
        expected["value"] = "test_value"
        expected["meta"] = {"test_meta":"dict"}
        expected["typeid"] = "epics:nt/NTAttribute:1.0"
        a = Attribute("test", self.meta)
        a.set_value("test_value")
        self.assertEquals(expected, a.to_dict())

    @patch.object(ScalarMeta, "from_dict")
    def test_from_dict(self, am_from_dict):
        am_from_dict.return_value = self.meta
        d = {"value":"test_value", "meta":{"meta":"dict"}}
        a = Attribute.from_dict("test", d)
        self.assertEquals("test", a.name)
        self.assertEquals("test_value", a.value)
        self.assertIs(self.meta, a.meta)

if __name__ == "__main__":
    unittest.main(verbosity=2)
