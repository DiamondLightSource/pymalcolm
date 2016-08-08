import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from collections import OrderedDict
from mock import MagicMock, patch

# module imports
from malcolm.gui.methoditem import MethodItem
from malcolm.core.response import Delta, Return, Error
from malcolm.core.request import Post


class TestMethodItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        MethodItem.items.clear()
        self.item = MethodItem(("endpoint",), ref)

    def test_get_writeable(self):
        self.assertEqual(self.item.get_writeable(), self.item.ref.writeable)

    def test_ref_children(self):
        self.item.ref.takes.elements = dict(a=1, b=2)
        self.assertEqual(self.item.ref_children(), 2)

    @patch("malcolm.gui.methoditem.ParameterItem")
    def test_create_children(self, parameter_mock):
        # Load up items to create
        pi1, pi2 = MagicMock(), MagicMock()
        parameter_mock.side_effect = [pi1, pi2]
        # Load up refs to get
        self.item.ref.takes.elements = OrderedDict((("p", 1), ("q", 2)))
        self.item.ref.defaults = dict(p=4)
        self.item.create_children()
        # Check it made the right thing
        self.assertEqual(len(self.item.children), 2)
        parameter_mock.assert_any_call(("endpoint", "takes", "elements", "p"), 1, 4)
        self.assertEqual(self.item.children[0], pi1)
        parameter_mock.assert_any_call(("endpoint", "takes", "elements", "q"), 2, None)
        self.assertEqual(self.item.children[1], pi2)

    def test_set_value(self):
        p1 = MagicMock()
        p2 = MagicMock()
        self.item.children = [p1, p2]
        p1.get_value.return_value = 43
        p1.endpoint = ("endpoint", "p1")
        p2.get_value.return_value = 1
        p2.endpoint = ("endpoint", "p2")
        request = self.item.set_value("anything")
        p1.reset_value.assert_called_once_with()
        p2.reset_value.assert_called_once_with()
        self.assertEqual(self.item.get_state(), self.item.RUNNING)
        self.assertEqual(request.parameters, dict(p1=43, p2=1))
        self.assertEqual(request.endpoint, ["endpoint"])
        self.assertIsInstance(request, Post)

    def test_handle_response_error(self):
        response = Error(None, None, "bad")
        self.item.handle_response(response)
        self.assertEqual(self.item.get_state(), self.item.ERROR)

    def test_handle_response_return(self):
        response = Return(None, None, "yay")
        self.item.handle_response(response)
        self.assertEqual(self.item.get_state(), self.item.IDLE)

    def test_handle_response_unknown(self):
        response = Delta(None, None, [])
        self.assertRaises(TypeError, self.item.handle_response, response)

if __name__ == "__main__":
    unittest.main(verbosity=2)

