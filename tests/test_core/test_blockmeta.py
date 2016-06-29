import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from mock import Mock

from malcolm.core.blockmeta import BlockMeta
from malcolm.core.serializable import Serializable

class TestBlockMeta(unittest.TestCase):
    def test_init(self):
        bm = BlockMeta("meta_name", "meta_description")
        self.assertEqual("meta_name", bm.name)
        self.assertEqual("meta_description", bm.description)
        self.assertEqual([], bm.tags)
        self.assertEqual("malcolm:core/BlockMeta:1.0", bm.typeid)

    def test_set_description(self):
        bm = BlockMeta("meta_name", "meta_description")
        bm.on_changed = Mock(wrap=bm.on_changed)
        bm.set_description("new_description")
        self.assertEquals("new_description", bm.description)
        bm.on_changed.assert_called_once_with(
            [["description"], "new_description"], True)

    def test_set_tags(self):
        bm = BlockMeta("meta_name", "meta_description")
        bm.on_changed = Mock(wrap=bm.on_changed)
        bm.set_tags(["new_tag"])
        self.assertEquals(["new_tag"], bm.tags)
        bm.on_changed.assert_called_once_with(
            [["tags"], ["new_tag"]], True)

    def test_update_description(self):
        bm = BlockMeta("meta_name", "")
        bm.on_changed = Mock(wrap=bm.on_changed)
        bm.update([["description"], "new_description"])
        self.assertEquals(bm.description, "new_description")
        bm.on_changed.assert_called_once_with(
            [["description"], "new_description"], True)

    def test_update_tags(self):
        bm = BlockMeta("meta_name", "")
        bm.on_changed = Mock(wrap=bm.on_changed)
        bm.update([["tags"], ["new_tag"]])
        self.assertEquals(bm.tags, ["new_tag"])
        bm.on_changed.assert_called_once_with(
            [["tags"], ["new_tag"]], True)

    def test_invalid_update_raises(self):
        bm = BlockMeta("meta_name", "")
        self.assertRaises(ValueError, bm.update, [["invalid_path"], ""])

    def test_substructure_update_raises(self):
        bm = BlockMeta("meta_name", "")
        self.assertRaises(
            ValueError, bm.update, [["tags", "invalid_substructure_path"], ""])

    def test_to_dict(self):
        bm = BlockMeta("meta_name", "meta_description")
        bm.tags = ["tag"]
        expected = OrderedDict()
        expected["description"] = "meta_description"
        expected["tags"] = ["tag"]
        expected["typeid"] = "malcolm:core/BlockMeta:1.0"
        self.assertEquals(expected, bm.to_dict())

    def test_from_dict(self):
        d = {"description":"test_description", "tags":["tag1", "tag2"],
             "typeid":"malcolm:core/BlockMeta:1.0"}
        bm = Serializable.from_dict("meta_name", d)
        self.assertEqual(BlockMeta, type(bm))
        self.assertEqual("meta_name", bm.name)
        self.assertEqual("test_description", bm.description)
        self.assertEqual(["tag1", "tag2"], bm.tags)
        self.assertEqual("malcolm:core/BlockMeta:1.0", bm.typeid)
        self.assertEqual(d, bm.to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
