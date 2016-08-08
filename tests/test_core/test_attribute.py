import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import Mock, patch

from malcolm.core.attribute import Attribute
from malcolm.core.serializable import Serializable
from malcolm.core.vmetas import StringMeta


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self.meta = StringMeta("something")

    def test_init(self):
        a = Attribute(self.meta)
        self.assertIs(self.meta, a.meta)
        self.assertIsNone(a.value)
        self.assertEquals("epics:nt/NTAttribute:1.0", a.typeid)


    def test_set_value(self):
        value = "test_value"
        a = Attribute(self.meta)
        a.report_changes = Mock(wrap=a.report_changes)
        a.set_value(value)
        self.assertEquals(a.value, value)
        a.report_changes.assert_called_once_with([['value'], value])



class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "epics:nt/NTAttribute:1.0"
        self.serialized["meta"] = StringMeta("desc").to_dict()
        self.serialized["value"] = "some string"

    def test_to_dict(self):
        a = Attribute(StringMeta("desc"))
        a.set_value("some string")
        self.assertEqual(a.to_dict(), self.serialized)

    def test_from_dict(self):
        a = Attribute.from_dict(self.serialized)
        self.assertEquals(a.meta._parent, a)
        self.assertEquals(a.meta.to_dict(), StringMeta("desc").to_dict())
        self.assertEquals(a.value, "some string")

if __name__ == "__main__":
    unittest.main(verbosity=2)
