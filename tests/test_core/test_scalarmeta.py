import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
from mock import Mock

from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable

# Register ScalarMeta as a sublcass of itself so we
# can instantiate it for testing purposes.
ScalarMeta.register("scalarmeta:test")(ScalarMeta)

class TestInit(unittest.TestCase):

    def setUp(self):
        self.meta = ScalarMeta("Test", "test description")

    def test_values_after_init(self):
        self.assertEqual("Test", self.meta.name)
        self.assertEqual("test description", self.meta.description)
        self.assertTrue(self.meta.writeable)

class TestValidate(unittest.TestCase):

    def setUp(self):
        self.meta = ScalarMeta("Test", "test_description")

    def test_given_validate_called_then_raise_error(self):

        expected_error_message = \
            "Abstract validate function must be implemented in child classes"

        with self.assertRaises(NotImplementedError) as error:
            self.meta.validate(1)

        self.assertEqual(expected_error_message, error.exception.args[0])

class TestUpdate(unittest.TestCase):

    def test_set_writeable(self):
        meta = ScalarMeta("Test", "test_description")
        meta.on_changed = Mock(wrap=meta.on_changed)
        writeable = Mock()
        notify = Mock()
        meta.set_writeable(writeable, notify=notify)
        self.assertEquals(meta.writeable, writeable)
        meta.on_changed.assert_called_once_with(
            [["writeable"], writeable], notify)

    def test_set_label(self):
        meta = ScalarMeta("Test", "test_description")
        meta.on_changed = Mock(wrap=meta.on_changed)
        label = Mock()
        notify = Mock()
        meta.set_label(label, notify=notify)
        self.assertEquals(meta.label, label)
        meta.on_changed.assert_called_once_with(
            [["label"], label], notify)

class TestDict(unittest.TestCase):

    def test_to_dict(self):
        meta = ScalarMeta("Test", "test_description")
        expected_dict = OrderedDict()
        expected_dict["typeid"] = "scalarmeta:test"
        expected_dict["description"] = "test_description"
        expected_dict["tags"] = ["tag"]
        expected_dict["writeable"] = True
        expected_dict["label"] = "Test"

        meta.tags = ["tag"]
        response = meta.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict(self):
        d = {"typeid":"scalarmeta:test", "description":"test_desc",
             "writeable":False, "tags":["tag"], "label":"test_label"}
        meta = Serializable.from_dict("Test", d)
        self.assertEqual("Test", meta.name)
        self.assertEqual("test_desc", meta.description)
        self.assertEqual(False, meta.writeable)
        self.assertEqual(["tag"], meta.tags)
        self.assertEqual("scalarmeta:test", meta.typeid)
        self.assertEqual("test_label", meta.label)
        self.assertEqual(d, meta.to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
