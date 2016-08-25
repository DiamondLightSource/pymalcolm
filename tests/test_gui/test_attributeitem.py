import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

# module imports
from malcolm.gui.attributeitem import AttributeItem
from malcolm.core.response import Error, Return, Delta


class TestAttributeItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        AttributeItem.items.clear()
        self.item = AttributeItem(("endpoint",), ref)

    def test_get_value(self):
        self.assertEqual(self.item.get_value(), str(self.item.ref.value))

    def test_get_writeable(self):
        self.assertEqual(self.item.get_writeable(), self.item.ref.meta.writeable)

    def test_set_value(self):
        value = MagicMock()
        request = self.item.set_value(value)
        self.assertEqual(AttributeItem.RUNNING, self.item.get_state())
        self.assertEqual(
            list(self.item.endpoint + ("value",)), request.endpoint)
        self.assertEqual(value.__str__.return_value, request.value)
        self.assertIsNone(request.response_queue)

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

