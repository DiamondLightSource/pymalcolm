import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from mock import Mock

# module imports
from malcolm.core.block import Block
from malcolm.core.blockmodel import BlockModel
from malcolm.core.attributemodel import AttributeModel
from malcolm.core.attribute import Attribute
from malcolm.core.methodmodel import MethodModel
from malcolm.core.view import make_view
from malcolm.vmetas.builtin import StringMeta


class TestBlock(unittest.TestCase):
    def setUp(self):
        self.data = BlockModel()
        self.data.set_endpoint_data("attr", StringMeta().create_attribute())
        self.data.set_endpoint_data("method", MethodModel())
        self.data.set_notifier_path(Mock(), ["block"])
        self.controller = Mock()
        self.context = Mock()
        self.o = make_view(self.controller, self.context, self.data, Block)

    def test_init(self):
        self.assertTrue(hasattr(self.o, "attr"))
        self.assertTrue(hasattr(self.o, "method"))
        self.assertTrue(hasattr(self.o, "method_async"))

    def test_put_attribute_values(self):
        self.o.put_attribute_values(dict(attr=43))
        self.context.put_async.assert_called_once_with(
            ["block", "attr", "value"], 43)
        self.context.wait_all_futures.assert_called_once_with(
            [self.context.put_async.return_value], timeout=None)

    def test_async_call(self):
        self.o.method_async(a=3)
        self.o.method.post_async.assert_called_once_with(a=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
