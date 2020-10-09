import unittest

from annotypes import Anno, add_call_types
from mock import Mock

from malcolm.core import (
    Attribute,
    BlockModel,
    Controller,
    MethodModel,
    Part,
    Process,
    StringMeta,
)
from malcolm.core.models import BlockMeta
from malcolm.core.views import make_view


class TestAttribute(unittest.TestCase):
    def setUp(self):
        self.data = StringMeta().create_attribute_model()
        self.data.set_notifier_path(Mock(), ["block", "attr"])
        self.controller = Mock()
        self.context = Mock()
        self.o = Attribute(self.controller, self.context, self.data)

    def test_init(self):
        self.assertIsInstance(self.o, Attribute)
        assert hasattr(self.o, "meta")
        assert hasattr(self.o, "value")
        assert hasattr(self.o, "subscribe_value")

    def test_put(self):
        self.o.put_value(32)
        self.context.put.assert_called_once_with(
            ["block", "attr", "value"], 32, timeout=None
        )

    def test_put_async(self):
        f = self.o.put_value_async(32)
        self.context.put_async.assert_called_once_with(["block", "attr", "value"], 32)
        assert f == self.context.put_async.return_value

    def test_repr(self):
        self.context.make_view.return_value = "foo"
        assert repr(self.o) == "<Attribute value='foo'>"
        self.context.make_view.assert_called_once_with(
            self.controller, self.data, "value"
        )


class TestBlock(unittest.TestCase):
    def setUp(self):
        self.data = BlockModel()
        self.data.set_endpoint_data("attr", StringMeta().create_attribute_model())
        self.data.set_endpoint_data("method", MethodModel())
        self.data.set_notifier_path(Mock(), ["block"])
        self.controller = Mock()
        self.context = Mock()
        self.o = make_view(self.controller, self.context, self.data)

    def test_init(self):
        assert hasattr(self.o, "attr")
        assert hasattr(self.o, "method")
        assert hasattr(self.o, "method_async")

    def test_put_attribute_values(self):
        self.o.put_attribute_values(dict(attr=43))
        self.context.put_async.assert_called_once_with(["block", "attr", "value"], 43)
        self.context.wait_all_futures.assert_called_once_with(
            [self.context.put_async.return_value], timeout=None, event_timeout=None
        )

    def test_async_call(self):
        self.o.method_async(a=3)
        self.o.method.post_async.assert_called_once_with(a=3)


with Anno("A Param"):
    AParam = str


class MyPart(Part):
    def setup(self, registrar):
        registrar.add_method_model(self.my_method, "myMethod")

    @add_call_types
    def my_method(self, param1: AParam, param2: AParam) -> AParam:
        return param1 + param2


class TestMethod(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.part = MyPart("test_part")
        self.controller = Controller("mri")
        self.controller.add_part(self.part)
        self.process.add_controller(self.controller)
        self.block = self.controller.block_view()
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_post(self):
        method_view = self.block.myMethod
        result = method_view.post(param1="testPost", param2="y")
        assert result == "testPosty"

    def test_post_async(self):
        method_view = self.block.myMethod
        f = method_view.post_async("testAsync", "y")
        assert f.result() == "testAsyncy"


class TestView(unittest.TestCase):
    def setUp(self):
        self.data = BlockMeta()
        self.data.set_notifier_path(Mock(), ["block", "meta"])
        self.controller = Mock()
        self.context = Mock()
        self.o = make_view(self.controller, self.context, self.data)

    def test_init(self):
        assert hasattr(self.o, "description")
        assert hasattr(self.o, "tags")
        assert hasattr(self.o, "writeable")
        assert hasattr(self.o, "label")

    def test_get_view(self):
        v = self.o.description
        self.context.make_view.assert_called_once_with(
            self.controller, self.data, "description"
        )
        assert v == self.context.make_view.return_value

    def test_second_subclass(self):
        data2 = {"a": 2}
        o2 = make_view(self.controller, self.context, data2)
        assert o2 == data2
