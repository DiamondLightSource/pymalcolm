import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock

from malcolm.core.attributemeta import AttributeMeta

# Register AttributeMeta as a sublcass of itself so we
# can instantiate it for testing purposes.
AttributeMeta.register_subclass("attribute_meta:test")(AttributeMeta)

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
        expected_dict["metaOf"] = "attribute_meta:test"

        response = self.attribute_meta.to_dict()

        self.assertEqual(expected_dict, response)

class TestFromDict(unittest.TestCase):

    def test_from_dict_returns(self):
        @AttributeMeta.register_subclass("foo:1.0")
        class Meta(AttributeMeta):
            from_dict = MagicMock()
        m = Meta("name", "desc")

        d = dict(metaOf = "foo:1.0")
        am = AttributeMeta.from_dict("me", d)

        m.from_dict.assert_called_once_with("me", d)
        self.assertEqual(m.from_dict.return_value, am)

    def test_from_dict_not_defined_on_subclass_fails(self):
        @AttributeMeta.register_subclass("anything")
        class Faulty(AttributeMeta):
            pass
        self.assertRaises(AssertionError, AttributeMeta.from_dict,
                          "me", dict(metaOf="anything"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
