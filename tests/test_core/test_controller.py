import unittest

from annotypes import Anno, add_call_types

from malcolm import __version__
from malcolm.core import (
    Controller,
    Error,
    Get,
    Part,
    PartRegistrar,
    Post,
    Process,
    Put,
    Queue,
    Return,
    StringMeta,
    Subscribe,
    Unsubscribe,
    Update,
)

with Anno("The return value"):
    AWorld = str


class MyPart(Part):
    my_attribute = None
    exception = None
    context = None

    @add_call_types
    def method(self) -> AWorld:
        return "world"

    def setup(self, registrar: PartRegistrar) -> None:
        self.my_attribute = StringMeta(description="MyString").create_attribute_model(
            "hello_block"
        )
        registrar.add_attribute_model(
            "myAttribute", self.my_attribute, self.my_attribute.set_value
        )
        registrar.add_method_model(self.method)


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = Process("proc")
        self.part = MyPart("test_part")
        self.o = Controller("mri")
        self.o.add_part(self.part)
        self.process.add_controller(self.o)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_init(self):
        assert self.o.mri == "mri"
        assert self.o.process == self.process

    def test_two_parts_same_attribute_fails(self):
        p2 = MyPart("another_part")
        with self.assertRaises(AssertionError) as cm:
            self.o.add_part(p2)
        assert str(cm.exception) == (
            "Field 'myAttribute' published by MyPart(name='another_part') "
            "would overwrite one made by MyPart(name='test_part')"
        )

    def test_make_view(self):
        b = self.process.block_view("mri")
        method_view = b.method
        attribute_view = b.myAttribute
        dict_view = b.method.meta.returns.elements
        list_view = b.method.meta.returns.required
        assert method_view() == "world"
        assert attribute_view.value == "hello_block"
        assert dict_view["return"].description == "The return value"
        assert list_view[0] == "return"
        assert b.meta.tags == ["version:pymalcolm:%s" % __version__]

    def test_handle_request(self):
        q = Queue()

        request = Get(id=41, path=["mri", "myAttribute"])
        request.set_callback(q.put)
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Return)
        assert response.id == 41
        assert response.value["value"] == "hello_block"
        self.part.my_attribute.meta.writeable = False
        request = Put(
            id=42, path=["mri", "myAttribute"], value="hello_block2", get=True
        )
        request.set_callback(q.put)
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Error)  # not writeable
        assert response.id == 42

        self.part.my_attribute.meta.writeable = True
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Return)
        assert response.id == 42
        assert response.value == "hello_block2"

        request = Post(id=43, path=["mri", "method"])
        request.set_callback(q.put)
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Return)
        assert response.id == 43
        assert response.value == "world"

        # cover the controller._handle_post path for parameters
        request = Post(id=43, path=["mri", "method"], parameters={"dummy": 1})
        request.set_callback(q.put)
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Error)
        assert response.id == 43
        assert (
            str(response.message)
            == "Given keys ['dummy'], some of which aren't in allowed keys []"
        )

        request = Subscribe(id=44, path=["mri", "myAttribute"], delta=False)
        request.set_callback(q.put)
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Update)
        assert response.id == 44
        assert response.value["typeid"] == "epics:nt/NTScalar:1.0"
        assert response.value["value"] == "hello_block2"

        request = Unsubscribe(id=44)
        request.set_callback(q.put)
        self.o.handle_request(request)
        response = q.get(timeout=0.1)
        self.assertIsInstance(response, Return)
        assert response.id == 44
