import unittest
from mock import MagicMock

from malcolm.gui.attributeitem import AttributeItem
from malcolm.core.response import Error, Return, Delta


class TestAttributeItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        AttributeItem.items.clear()
        self.item = AttributeItem(("endpoint",), ref)

    def test_get_value(self):
        assert self.item.get_value() == str(self.item.ref.value)

    def test_get_writeable(self):
        assert self.item.get_writeable() == self.item.ref.meta.writeable

    def test_set_value(self):
        value = MagicMock()
        request = self.item.set_value(value)
        assert AttributeItem.RUNNING == self.item.get_state()
        assert (
            list(self.item.endpoint + ("value",))) == request.path
        assert value.__str__.return_value == request.value

    def test_handle_response_error(self):
        response = Error(message="bad")
        self.item.handle_response(response)
        assert self.item.get_state() == self.item.ERROR

    def test_handle_response_return(self):
        response = Return(value="yay")
        self.item.handle_response(response)
        assert self.item.get_state() == self.item.IDLE

    def test_handle_response_unknown(self):
        response = Delta(changes=[])
        with self.assertRaises(TypeError):
            self.item.handle_response(response)
