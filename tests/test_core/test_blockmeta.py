import os
import sys
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

from malcolm.core.blockmeta import BlockMeta


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/BlockMeta:1.0"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = ()
        self.serialized["writeable"] = False
        self.serialized["label"] = ""
        self.serialized["fields"] = ()

    def test_to_dict(self):
        m = BlockMeta("desc")
        self.assertEqual(m.to_dict(), self.serialized)

    def test_from_dict(self):
        m = BlockMeta.from_dict(self.serialized)
        self.assertEquals(m.description, "desc")
        self.assertEquals(m.tags, ())
        self.assertEquals(m.writeable, False)
        self.assertEquals(m.label, "")

if __name__ == "__main__":
    unittest.main(verbosity=2)
