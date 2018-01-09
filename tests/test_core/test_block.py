import unittest
from mock import Mock

from malcolm.core.views import make_block_view
from malcolm.core import BlockModel
from malcolm.core.methodmodel import MethodModel
from malcolm.core.vmetas import StringMeta


class TestBlock(unittest.TestCase):
    def setUp(self):
        self.data = BlockModel()
        self.data.set_endpoint_data("attr", StringMeta().create_attribute_model())
        self.data.set_endpoint_data("method", MethodModel())
        self.data.set_notifier_path(Mock(), ["block"])
        self.controller = Mock()
        self.context = Mock()
        self.o = make_block_view(self.controller, self.context, self.data)

    def test_init(self):
        assert hasattr(self.o, "attr")
        assert hasattr(self.o, "method")
        assert hasattr(self.o, "method_async")

    def test_put_attribute_values(self):
        self.o.put_attribute_values(dict(attr=43))
        self.context.put_async.assert_called_once_with(
            ["block", "attr", "value"], 43)
        self.context.wait_all_futures.assert_called_once_with(
            [self.context.put_async.return_value], timeout=None)

    def test_async_call(self):
        self.o.method_async(a=3)
        self.o.method.post_async.assert_called_once_with(a=3)
