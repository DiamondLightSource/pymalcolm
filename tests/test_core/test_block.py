import unittest
from collections import OrderedDict
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock, patch

# module imports
from malcolm.core.block import Block


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block("blockname")
        self.assertEqual(b.name, "blockname")
        self.assertEqual(b._methods.keys(), [])

    def test_add_method_registers(self):
        b = Block("blockname")
        m = MagicMock()
        m.name = "mymethod"
        b.add_method(m)
        self.assertEqual(b._methods.keys(), ["mymethod"])
        self.assertFalse(m.called)
        m.return_value = 42
        self.assertEqual(b.mymethod(), 42)
        m.assert_called_once_with()


class TestToDict(unittest.TestCase):

    @patch('malcolm.core.method.Method.to_dict')
    def test_returns_dict(self, method_to_dict_mock):
        method_dict_1 = OrderedDict(takes=OrderedDict(one=OrderedDict()),
                                    returns=OrderedDict(one=OrderedDict()),
                                    defaults=OrderedDict())
        method_dict_2 = OrderedDict(takes=OrderedDict(one=OrderedDict()),
                                    returns=OrderedDict(one=OrderedDict()),
                                    defaults=OrderedDict())
        method_to_dict_mock.side_effect = [method_dict_1, method_dict_2]

        m1 = MagicMock()
        m1.name = "method_one"
        m1.to_dict.return_value = method_dict_1

        m2 = MagicMock()
        m2.name = "method_two"
        m2.to_dict.return_value = method_dict_2

        self.meta_map = Block("Test")
        self.meta_map.add_method(m1)
        self.meta_map.add_method(m2)

        expected_methods_dict = OrderedDict()
        expected_methods_dict['method_one'] = method_dict_1
        expected_methods_dict['method_two'] = method_dict_2

        expected_dict = OrderedDict()
        expected_dict['methods'] = expected_methods_dict

        response = self.meta_map.to_dict()

        self.assertEqual(expected_dict, response)

if __name__ == "__main__":
    unittest.main(verbosity=2)
