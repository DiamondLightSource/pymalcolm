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

class TestToDict(unittest.TestCase):

    def setUp(self):
        self.meta = ScalarMeta("Test", "test_description")

    def test_returns_dict(self):
        expected_dict = OrderedDict()
        expected_dict["typeid"] = "scalarmeta:test"
        expected_dict["description"] = "test_description"
        expected_dict["tags"] = ["tag"]
        expected_dict["writeable"] = True

        self.meta.tags = ["tag"]
        response = self.meta.to_dict()

        self.assertEqual(expected_dict, response)

if __name__ == "__main__":
    unittest.main(verbosity=2)
