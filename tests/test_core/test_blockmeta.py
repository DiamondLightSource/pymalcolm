import unittest
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
        assert m.to_dict() == self.serialized

    def test_from_dict(self):
        m = BlockMeta.from_dict(self.serialized)
        assert m.description == "desc"
        assert m.tags == ()
        assert m.writeable == False
        assert m.label == ""
