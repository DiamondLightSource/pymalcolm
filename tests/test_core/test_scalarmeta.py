import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
from mock import Mock

from malcolm.core.scalarmeta import ScalarMeta

# Register ScalarMeta as a sublcass of itself so we
# can instantiate it for testing purposes.
ScalarMeta.register("attribute_meta:test")(ScalarMeta)

class TestInit(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = ScalarMeta("Test", "test description")

    def test_values_after_init(self):
        self.assertEqual("Test", self.attribute_meta.name)
        self.assertEqual("test description", self.attribute_meta.description)
        self.assertTrue(self.attribute_meta.writeable)

class TestValidate(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = ScalarMeta("Test", "test_description")

    def test_given_validate_called_then_raise_error(self):

        expected_error_message = \
            "Abstract validate function must be implemented in child classes"

        with self.assertRaises(NotImplementedError) as error:
            self.attribute_meta.validate(1)

        self.assertEqual(expected_error_message, error.exception.args[0])

class TestUpdate(unittest.TestCase):

    def test_set_writeable(self):
        attribute_meta = ScalarMeta("Test", "test_description")
        attribute_meta.on_changed = Mock(wrap=attribute_meta.on_changed)
        writeable = Mock()
        notify = Mock()
        attribute_meta.set_writeable(writeable, notify=notify)
        self.assertEquals(attribute_meta.writeable, writeable)
        attribute_meta.on_changed.assert_called_once_with(
            [["writeable"], writeable], notify)

class TestToDict(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = ScalarMeta("Test", "test_description")

    def test_returns_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test_description"
        expected_dict["typeid"] = "attribute_meta:test"

        response = self.attribute_meta.to_dict()

        self.assertEqual(expected_dict, response)

if __name__ == "__main__":
    unittest.main(verbosity=2)
