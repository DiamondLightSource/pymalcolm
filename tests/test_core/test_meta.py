import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from mock import Mock

from malcolm.core.meta import Meta
from malcolm.core.serializable import Serializable

Serializable.register("meta:test")(Meta)

class TestMeta(unittest.TestCase):
    def test_init(self):
        meta = Meta("meta_name", "meta_description")
        self.assertEqual("meta_name", meta.name)
        self.assertEqual("meta_description", meta.description)
        self.assertEqual([], meta.tags)

    def test_set_description(self):
        meta = Meta("meta_name", "meta_description")
        meta.on_changed = Mock(wrap=meta.on_changed)
        meta.set_description("new_description")
        self.assertEquals("new_description", meta.description)
        meta.on_changed.assert_called_once_with(
            [["description"], "new_description"], True)

    def test_set_tags(self):
        meta = Meta("meta_name", "meta_description")
        meta.on_changed = Mock(wrap=meta.on_changed)
        meta.set_tags(["new_tag"])
        self.assertEquals(["new_tag"], meta.tags)
        meta.on_changed.assert_called_once_with(
            [["tags"], ["new_tag"]], True)

    def test_update_description(self):
        meta = Meta("meta_name", "")
        meta.on_changed = Mock(wrap=meta.on_changed)
        meta.update([["description"], "new_description"])
        self.assertEquals(meta.description, "new_description")
        meta.on_changed.assert_called_once_with(
            [["description"], "new_description"], True)

    def test_update_tags(self):
        meta = Meta("meta_name", "")
        meta.on_changed = Mock(wrap=meta.on_changed)
        meta.update([["tags"], ["new_tag"]])
        self.assertEquals(meta.tags, ["new_tag"])
        meta.on_changed.assert_called_once_with(
            [["tags"], ["new_tag"]], True)

    def test_invalid_update_raises(self):
        meta = Meta("meta_name", "")
        self.assertRaises(ValueError, meta.update, [["invalid_path"], ""])

    def test_substructure_update_raises(self):
        meta = Meta("meta_name", "")
        self.assertRaises(
            ValueError, meta.update, [["tags", "invalid_substructure_path"], ""])

    def test_to_dict(self):
        meta = Meta("meta_name", "meta_description")
        meta.tags = ["tag"]
        expected = OrderedDict()
        expected["typeid"] = "meta:test"
        expected["description"] = "meta_description"
        expected["tags"] = ["tag"]
        self.assertEquals(expected, meta.to_dict())

    def test_from_dict(self):
        d = {"description":"test_description", "tags":["tag1", "tag2"],
             "typeid":"meta:test"}
        meta = Serializable.from_dict("meta_name", d)
        self.assertEqual(Meta, type(meta))
        self.assertEqual("meta_name", meta.name)
        self.assertEqual("test_description", meta.description)
        self.assertEqual(["tag1", "tag2"], meta.tags)
        self.assertEqual(d, meta.to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
