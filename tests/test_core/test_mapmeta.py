import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, patch, call

from malcolm.core.mapmeta import MapMeta


class TestInit(unittest.TestCase):

    def setUp(self):
        self.meta_map = MapMeta("Test", "description")

    def test_values_set(self):
        self.assertEqual(self.meta_map.name, "Test")
        self.assertIsInstance(self.meta_map.elements, OrderedDict)
        self.assertEqual(self.meta_map.elements, {})
        self.assertEqual("malcolm:core/MapMeta:1.0", self.meta_map.typeid)
        self.assertEqual("description", self.meta_map.description)

class TestValidate(unittest.TestCase):

    def setUp(self):
        self.meta_map = MapMeta("Test", "description")

    def test_given_valid_elements_then_return(self):
        self.meta_map.elements = dict(Arg1="Meta1", Arg2="Meta2")
        self.meta_map.required = ["Arg1"]

        self.meta_map.validate(dict(Arg1="Instance1"))

    def test_given_invalid_element_then_raise(self):
        self.meta_map.elements = dict(Arg1="Meta1", Arg2="Meta2")
        self.meta_map.required = ["Arg1"]

        with self.assertRaises(KeyError):
            self.meta_map.validate(dict(Arg3="Instance1"))

    def test_missing_required_element_then_raise(self):
        self.meta_map.elements = dict(Arg1="Meta1", Arg2="Meta2")
        self.meta_map.required = ["Arg1"]

        with self.assertRaises(KeyError):
            self.meta_map.validate(dict(Arg2="Instance1"))


class TestAddElement(unittest.TestCase):

    def setUp(self):
        self.meta_map = MapMeta("Test", "description")
        self.attribute_mock = MagicMock()

    def test_given_valid_required_element_then_add(self):
        self.meta_map.add_element(self.attribute_mock, required=True)

        self.assertEqual(self.attribute_mock,
                         self.meta_map.elements[self.attribute_mock.name])
        self.assertEqual([self.attribute_mock.name], self.meta_map.required)

    def test_given_valid_optional_element_then_add(self):
        self.meta_map.add_element(self.attribute_mock, required=False)

        self.assertEqual(self.attribute_mock,
                         self.meta_map.elements[self.attribute_mock.name])
        self.assertEqual([], self.meta_map.required)

    def test_given_existing_element_then_raise_error(self):
        self.meta_map.add_element(self.attribute_mock, required=False)
        expected_error_message = "Element already exists in dictionary"

        with self.assertRaises(ValueError) as error:
            self.meta_map.add_element(self.attribute_mock, required=False)

        self.assertEqual(expected_error_message, error.exception.args[0])


class TestToDict(unittest.TestCase):

    def test_returns_dict(self):
        e1 = MagicMock()
        e1.name = "one"
        a1 = OrderedDict()
        e1.to_dict.return_value = a1
        e2 = MagicMock()
        e2.name = "two"
        a2 = OrderedDict()
        e2.to_dict.return_value = a2

        self.meta_map = MapMeta("Test", "description")
        self.meta_map.add_element(e1, required=True)
        self.meta_map.add_element(e2, required=False)

        expected_elements_dict = OrderedDict()
        expected_elements_dict['one'] = a1
        expected_elements_dict['two'] = a2

        expected_dict = OrderedDict()
        expected_dict['typeid'] = 'malcolm:core/MapMeta:1.0'
        expected_dict['elements'] = expected_elements_dict
        expected_dict['description'] = 'description'
        expected_dict['tags'] = []
        expected_dict['required'] = ['one']

        response = self.meta_map.to_dict()

        self.assertEqual(expected_dict, response)

    @patch('malcolm.core.mapmeta.Serializable')
    def test_from_dict_deserialize(self, am_mock):
        # prep dict
        elements = OrderedDict()
        elements["one"] = "e1"
        elements["two"] = "e2"
        required = ["one"]
        d = dict(elements=elements, required=required,
            description="desc", tags=["tag"])
        # prep from_dict with ScalarMetas to return
        am1 = MagicMock()
        am1.name = "one"
        am2 = MagicMock()
        am2.name = "two"
        am_mock.deserialize.side_effect = [am1, am2]

        map_meta = MapMeta.from_dict("Test", d)

        self.assertEqual(am_mock.deserialize.call_args_list, [
            call("one", "e1"), call("two", "e2")])
        self.assertEqual(map_meta.name, "Test")
        self.assertEqual(map_meta.required, ["one"])
        self.assertEqual(map_meta.elements, dict(one=am1, two=am2))
        self.assertEqual(map_meta.description, "desc")
        self.assertEqual(map_meta.tags, ["tag"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
