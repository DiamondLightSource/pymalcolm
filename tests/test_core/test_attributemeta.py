import unittest
from collections import OrderedDict

from malcolm.core.attributemeta import AttributeMeta

from pkg_resources import require
require("mock")
from mock import MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestInit(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test")

    def test_given_name_then_set(self):
        self.assertEqual("Test", self.attribute_meta.name)


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test")

    def test_given_validate_called_then_raise_error(self):

        expected_error_message = \
            "Abstract validate function must be implemented in child classes"

        with self.assertRaises(NotImplementedError) as error:
            self.attribute_meta.validate(1)

        self.assertEqual(expected_error_message, error.exception.message)


class TestToDict(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test")

    def test_returns_dict(self):
        expected_dict = OrderedDict()
        expected_dict["metaOf"] = None

        response = self.attribute_meta.to_dict()

        self.assertEqual(expected_dict, response)

class TestFromDict(unittest.TestCase):

    def test_from_dict_returns(self):
        m = MagicMock()
        AttributeMeta.register_subclass(m, "foo:1.0")
        self.assertEqual(m.metaOf, "foo:1.0")

        d = dict(metaOf = "foo:1.0")
        am = AttributeMeta.from_dict("me", d)

        m.from_dict.assert_called_once_with("me", d)
        self.assertEqual(m.from_dict.return_value, am)

    def test_from_dict_not_defined_on_subclass_fails(self):
        class Faulty(AttributeMeta):
            pass
        AttributeMeta.register_subclass(Faulty, "anything")
        self.assertRaises(AssertionError, AttributeMeta.from_dict,
                          "me", dict(metaOf="anything"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
