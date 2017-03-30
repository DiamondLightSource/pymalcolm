import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest

from malcolm.core.elementmap import ElementMap
from malcolm.core.vmetas import StringArrayMeta
from malcolm.core.mapmeta import MapMeta


class TestSetters(unittest.TestCase):

    def setUp(self):
        self.mm = MapMeta("description")

    def test_values_set(self):
        self.assertIsInstance(self.mm.elements, ElementMap)
        self.assertEqual(len(self.mm.elements), 0)
        self.assertEqual(self.mm.typeid, "malcolm:core/MapMeta:1.0")
        self.assertEqual(self.mm.description, "description")

    def test_set_elements(self):
        els = ElementMap(dict(sam=StringArrayMeta()))
        self.mm.set_elements(els)
        self.assertEqual(self.mm.elements, els)

    def test_set_required(self):
        self.test_set_elements()
        req = ("sam",)
        self.mm.set_required(req)
        self.assertEqual(self.mm.required, req)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.sam = StringArrayMeta()
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/MapMeta:1.0"
        self.serialized["elements"] = ElementMap(dict(c1=self.sam)).to_dict()
        self.serialized["description"] = "desc"
        self.serialized["tags"] = ()
        self.serialized["writeable"] = False
        self.serialized["label"] = ""
        self.serialized["required"] = ("c1",)

    def test_to_dict(self):
        tm = MapMeta("desc")
        tm.set_elements(ElementMap(dict(c1=self.sam)))
        tm.set_required(["c1"])
        self.assertEqual(tm.to_dict(), self.serialized)

    def test_from_dict(self):
        tm = MapMeta.from_dict(self.serialized)
        self.assertEquals(tm.description, "desc")
        self.assertEquals(len(tm.elements), 1)
        self.assertEquals(tm.elements["c1"].to_dict(), self.sam.to_dict())
        self.assertEquals(tm.tags, ())
        self.assertEquals(tm.required, ("c1",))


if __name__ == "__main__":
    unittest.main(verbosity=2)
