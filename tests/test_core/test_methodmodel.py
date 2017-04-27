from collections import OrderedDict
import unittest

from malcolm.core.methodmodel import MethodModel, method_takes, REQUIRED, \
    method_returns, method_writeable_in, OPTIONAL, method_also_takes
from malcolm.modules.builtin.vmetas import StringMeta, BooleanMeta
from malcolm.core.mapmeta import MapMeta


class TestMethodMeta(unittest.TestCase):

    def test_init(self):
        m = MethodModel("test_description")
        self.assertEquals("test_description", m.description)
        self.assertEquals("malcolm:core/Method:1.0", m.typeid)
        self.assertEquals("", m.label)

    def test_set_label(self):
        m = MethodModel("test_description")
        m.set_label("new_label")
        self.assertEquals("new_label", m.label)

    def test_recreate(self):
        @method_takes(
            "arg1", StringMeta("Arg1"), REQUIRED,
            "extra", StringMeta(), REQUIRED,
        )
        def method1():
            pass

        @method_takes(
            "arg8", StringMeta("Arg8"), REQUIRED,
            "arg3", StringMeta("Arg3"), "32",
            "arg4", StringMeta("Arg4"), OPTIONAL,
        )
        def method2():
            pass

        @method_takes(
            "arg8", StringMeta("Arg8"), "2",
            "arg3", StringMeta("Arg3"), "33",
        )
        def method3():
            pass

        m = MethodModel("Test")
        m.recreate_from_others([
            method1.MethodModel, method2.MethodModel, method3.MethodModel],
            without=["extra"])

        itakes = MapMeta()
        elements = OrderedDict()
        elements["arg1"] = StringMeta("Arg1")
        elements["arg8"] = StringMeta("Arg8")
        elements["arg3"] = StringMeta("Arg3")
        elements["arg4"] = StringMeta("Arg4")
        itakes.set_elements(elements)
        itakes.set_required(["arg1"])
        defaults = OrderedDict()
        defaults["arg8"] = "2"
        defaults["arg3"] = "33"
        self.assertEqual(m.takes.to_dict(), itakes.to_dict())
        self.assertEqual(m.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(m.defaults, defaults)


class TestDecorators(unittest.TestCase):
    def test_takes_given_optional(self):
        @method_takes("hello", StringMeta(), OPTIONAL)
        def say_hello(params):
            """Say hello"""
            print("Hello" + params.name)

        itakes = MapMeta()
        itakes.set_elements(OrderedDict(hello=StringMeta()))
        self.assertEqual(say_hello.MethodModel.takes.to_dict(), itakes.to_dict())
        self.assertEqual(say_hello.MethodModel.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.MethodModel.defaults, {})

    def test_takes_given_defaults(self):
        @method_takes("hello", StringMeta(), "Something")
        def say_hello(params):
            """Say hello"""
            print("Hello" + params.name)

        itakes = MapMeta()
        itakes.set_elements(OrderedDict(hello=StringMeta()))
        self.assertEqual(say_hello.MethodModel.takes.to_dict(), itakes.to_dict())
        self.assertEqual(say_hello.MethodModel.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.MethodModel.defaults, {"hello": "Something"})

    def test_takes_given_required(self):
        @method_takes("hello", StringMeta(), REQUIRED)
        def say_hello(params):
            """Say hello"""
            print("Hello" + params.name)

        itakes = MapMeta()
        itakes.set_elements(OrderedDict(hello=StringMeta()))
        itakes.set_required(["hello"])
        self.assertEqual(say_hello.MethodModel.takes.to_dict(), itakes.to_dict())
        self.assertEqual(say_hello.MethodModel.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.MethodModel.defaults, {})

    def test_returns_given_valid_sets(self):
        @method_returns("hello", StringMeta(), REQUIRED)
        def say_hello(ret):
            """Say hello"""
            ret.hello = "Hello"
            return ret

        ireturns = MapMeta()
        ireturns.set_elements(OrderedDict(hello=StringMeta()))
        ireturns.set_required(["hello"])
        self.assertEqual(say_hello.MethodModel.takes.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.MethodModel.returns.to_dict(), ireturns.to_dict())
        self.assertEqual(say_hello.MethodModel.defaults, {})

    def test_returns_not_given_req_or_opt_raises(self):
        with self.assertRaises(AssertionError):
            @method_returns("hello", StringMeta(), "A default")
            def say_hello(ret):
                """Say hello"""
                ret.hello = "Hello"
                return ret

    def test_only_in(self):
        @method_writeable_in("boo", "boo2")
        def f():
            pass

        self.assertTrue(hasattr(f, "MethodModel"))
        self.assertEqual(f.MethodModel.writeable_in, ("boo", "boo2"))

    def test_method_also_takes(self):
        @method_takes(
            "hello", StringMeta(), REQUIRED,
            "hello2", BooleanMeta(), False)
        class Thing(object):
            pass

        @method_also_takes(
            "world", BooleanMeta(), REQUIRED,
            "hello2", BooleanMeta(), True,
            "default", StringMeta(), "nothing")
        class Thing2(Thing):
            pass

        # Check original hasn't been modified
        itakes = MapMeta()
        elements = OrderedDict()
        elements["hello"] = StringMeta()
        elements["hello2"] = BooleanMeta()
        itakes.set_elements(elements)
        itakes.set_required(["hello"])
        defaults = OrderedDict()
        defaults["hello2"] = False
        self.assertEqual(Thing.MethodModel.takes.to_dict(), itakes.to_dict())
        self.assertEqual(Thing.MethodModel.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(Thing.MethodModel.defaults, defaults)

        # Check new one overrides/improves on original
        itakes = MapMeta()
        elements = OrderedDict()
        elements["hello"] = StringMeta()
        elements["hello2"] = BooleanMeta()
        elements["world"] = BooleanMeta()
        elements["default"] = StringMeta()
        itakes.set_elements(elements)
        itakes.set_required(["hello", "world"])
        defaults = OrderedDict()
        defaults["hello2"] = True
        defaults["default"] = "nothing"
        self.assertEqual(Thing2.MethodModel.takes.to_dict(), itakes.to_dict())
        self.assertEqual(Thing2.MethodModel.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(Thing2.MethodModel.defaults, defaults)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/Method:1.0"
        self.takes = MapMeta()
        self.takes.set_elements({"in_attr": StringMeta("desc")})
        self.serialized["takes"] = self.takes.to_dict()
        self.serialized["defaults"] = OrderedDict({"in_attr": "default"})
        self.serialized["description"] = "test_description"
        self.serialized["tags"] = ()
        self.serialized["writeable"] = True
        self.serialized["label"] = ""
        self.serialized["returns"] = MapMeta().to_dict()

    def test_to_dict(self):
        m = MethodModel("test_description")
        m.set_takes(self.takes)
        m.set_defaults(self.serialized["defaults"])
        self.assertEqual(m.to_dict(), self.serialized)

    def test_from_dict(self):
        m = MethodModel.from_dict(self.serialized)
        self.assertEqual(m.takes.to_dict(), self.takes.to_dict())
        self.assertEqual(m.defaults, self.serialized["defaults"])
        self.assertEqual(m.tags, ())
        self.assertEqual(m.writeable, True)
        self.assertEqual(m.label, "")
        self.assertEqual(m.returns.to_dict(), MapMeta().to_dict())
