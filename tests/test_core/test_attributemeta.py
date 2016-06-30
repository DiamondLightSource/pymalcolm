import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.attributemeta import AttributeMeta

# Register AttributeMeta as a sublcass of itself so we
# can instantiate it for testing purposes.
AttributeMeta.register("attribute_meta:test")(AttributeMeta)

class TestInit(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test", "test description")

    def test_values_after_init(self):
        self.assertEqual("Test", self.attribute_meta.name)
        self.assertEqual("test description", self.attribute_meta.description)

class TestValidate(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test", "test_description")

    def test_given_validate_called_then_raise_error(self):

        expected_error_message = \
            "Abstract validate function must be implemented in child classes"

        with self.assertRaises(NotImplementedError) as error:
            self.attribute_meta.validate(1)

        self.assertEqual(expected_error_message, error.exception.args[0])


class TestToDict(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test", "test_description")

    def test_returns_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test_description"
        expected_dict["typeid"] = "attribute_meta:test"

        response = self.attribute_meta.to_dict()

        self.assertEqual(expected_dict, response)

if __name__ == "__main__":
    unittest.main(verbosity=2)
