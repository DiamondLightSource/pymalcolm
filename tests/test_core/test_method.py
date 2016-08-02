import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import Mock, patch, call, MagicMock

from malcolm.core.method import Method, takes, returns, only_in, OPTIONAL, \
    REQUIRED
from malcolm.core.meta import Meta
from malcolm.metas.mapmeta import MapMeta
from malcolm.metas.stringmeta import StringMeta
from malcolm.core.serializable import Serializable

from malcolm.metas import MapMeta, StringMeta


class TestMethod(unittest.TestCase):

    def test_init(self):
        m = Method("test_description")
        self.assertEquals("test_description", m.description)
        self.assertEquals("malcolm:core/Method:1.0", m.typeid)
        self.assertEquals("", m.label)

    def test_set_label(self):
        m = Method("test_description")
        m.on_changed = Mock(wrap=m.on_changed)
        m.set_label("new_label")
        self.assertEquals("new_label", m.label)
        m.on_changed.assert_called_once_with([["label"], "new_label"], True)

    def test_call_calls_call_function(self):
        m = Method("test_description")
        call_func_mock = MagicMock()
        call_func_mock.return_value = {"output": 2}
        m.call_function = call_func_mock
        func = Mock(return_value={"first_out": "test"})
        m.set_function(func)
        args_meta = Mock(spec=MapMeta)
        args_meta.elements = {"first": Mock()}
        m.set_takes(args_meta)

        response = m(first="test")

        call_func_mock.assert_called_once_with(dict(first="test"))
        self.assertEqual(response, {"output": 2})

    def test_call_with_positional_args(self):
        func = Mock(return_value={"output": 2})
        m = Method("test_description")
        call_func_mock = MagicMock()
        m.call_function = call_func_mock
        m.set_function(func)
        args_meta = Mock(spec=MapMeta)
        validator = Mock(return_value=True)
        args_meta.elements = OrderedDict()
        args_meta.elements["first"] = Mock(validate=validator)
        args_meta.elements["second"] = Mock(validate=validator)
        args_meta.elements["third"] = Mock(validate=validator)
        args_meta.elements["fourth"] = Mock(validate=validator)
        args_meta.required = ["first", "third"]
        m.set_takes(args_meta)

        m(2, 3, third=1, fourth=4)

        call_func_mock.assert_called_once_with({'second': 3, 'fourth': 4,
                                                'third': 1, 'first': 2})

    def test_get_response_calls_call_function(self):
        m = Method("test_description")
        m.set_logger_name("mname")
        call_func_mock = MagicMock()
        m.call_function = call_func_mock
        func = Mock(return_value={"first_out": "test"})
        m.set_function(func)
        args_meta = Mock(spec=MapMeta)
        args_meta.elements = {"first": Mock()}
        m.set_takes(args_meta)
        request = MagicMock()
        request.parameters = dict(first="test")

        m.get_response(request)

        call_func_mock.assert_called_once_with(dict(first="test"))

    def test_get_response_no_parameters(self):
        m = Method("test_description")
        m.set_logger_name("mname")
        call_func_mock = MagicMock()
        m.call_function = call_func_mock
        func = Mock(return_value={"first_out": "test"})
        m.set_function(func)
        args_meta = Mock(spec=MapMeta)
        args_meta.elements = {"first": Mock()}
        m.set_takes(args_meta)
        request = MagicMock()
        del request.parameters  # Make sure mock doesn't have `parameters`

        m.get_response(request)

        call_func_mock.assert_called_once_with(dict())

    def test_get_response_raises(self):
        func = MagicMock()
        func.side_effect = ValueError("Test error")
        m = Method("test_description")
        m.set_parent(Mock(), "test_method")
        m.set_function(func)
        m.takes = MagicMock()
        m.returns = MagicMock()
        request = MagicMock()

        response = m.get_response(request)
        self.assertEquals("malcolm:core/Error:1.0", response.typeid)
        self.assertEquals(
            "Method test_method raised an error: Test error", response.message)

    def test_defaults(self):
        func = Mock(return_value={"first_out": "test"})
        m = Method("test_description", writeable=True)
        m.set_parent(Mock(), "test_method")
        s = StringMeta(description='desc')
        args_meta = MapMeta()
        args_meta.elements = {"first": s, "second": s}
        m.set_takes(args_meta)
        m.set_defaults({"second": "default"})
        m.set_function(func)

        self.assertEquals({"first_out": "test"}, m.call_function(dict(first="test")))
        call_arg = func.call_args[0][0]
        self.assertEqual("test", call_arg.first)
        self.assertEqual("default", call_arg.second)
        self.assertEqual(args_meta, call_arg.meta)

    def test_incomplete_return(self):
        func = Mock(return_value={"output1": 2})
        m = Method("test_description", writeable=True)
        m.name = "test_method"
        m.set_function(func)
        s = StringMeta(description='desc')
        args_meta = MapMeta()
        args_meta.set_elements({"first": s, "second": s})
        return_meta = MapMeta()
        return_meta.set_elements({"output1": s, "output2": s})
        return_meta.set_required(["output2"])
        m.set_takes(args_meta)
        m.set_returns(return_meta)

        with self.assertRaises(KeyError):
            m.call_function(dict(first=1, second=2))
        call_arg1, call_arg2 = func.call_args_list[0][0]
        self.assertEqual('1', call_arg1.first)
        self.assertEqual('2', call_arg1.second)
        self.assertEqual(args_meta, call_arg1.meta)
        self.assertEqual(return_meta, call_arg2.meta)

    @patch('malcolm.core.method.Method.call_function')
    def test_handle_request(self, call_function_mock):
        call_function_mock.return_value = {"output": 1}
        m = Method("test_description")
        m.set_logger_name("mname")
        request = Mock(
                id=(123, Mock()), type="Post", parameters={"first": 2},
                respond_with_return=Mock())

        response = m.get_response(request)

        call_function_mock.assert_called_with({"first": 2})
        self.assertEquals({"output": 1}, response.value)

    def test_not_writeable_stops_call(self):
        m = Method("test_description")
        m.set_function(Mock())
        m.set_writeable(False)
        with self.assertRaises(ValueError,
                msg="Cannot call a method that is not writeable"):
            m()



class TestDecorators(unittest.TestCase):
    def test_takes_given_optional(self):
        @takes("hello", StringMeta(), OPTIONAL)
        def say_hello(params):
            """Say hello"""
            print("Hello" + params.name)

        itakes = MapMeta()
        itakes.set_elements(OrderedDict(hello=StringMeta()))
        self.assertEqual(say_hello.Method.takes.to_dict(), itakes.to_dict())
        self.assertEqual(say_hello.Method.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.Method.defaults, {})

    def test_takes_given_defaults(self):
        @takes("hello", StringMeta(), "Something")
        def say_hello(params):
            """Say hello"""
            print("Hello" + params.name)

        itakes = MapMeta()
        itakes.set_elements(OrderedDict(hello=StringMeta()))
        self.assertEqual(say_hello.Method.takes.to_dict(), itakes.to_dict())
        self.assertEqual(say_hello.Method.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.Method.defaults, {"hello": "Something"})

    def test_takes_given_required(self):
        @takes("hello", StringMeta(), REQUIRED)
        def say_hello(params):
            """Say hello"""
            print("Hello" + params.name)

        itakes = MapMeta()
        itakes.set_elements(OrderedDict(hello=StringMeta()))
        itakes.set_required(["hello"])
        self.assertEqual(say_hello.Method.takes.to_dict(), itakes.to_dict())
        self.assertEqual(say_hello.Method.returns.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.Method.defaults, {})

    def test_returns_given_valid_sets(self):
        @returns("hello", StringMeta(), REQUIRED)
        def say_hello(ret):
            """Say hello"""
            ret.hello = "Hello"
            return ret

        ireturns = MapMeta()
        ireturns.set_elements(OrderedDict(hello=StringMeta()))
        ireturns.set_required(["hello"])
        self.assertEqual(say_hello.Method.takes.to_dict(), MapMeta().to_dict())
        self.assertEqual(say_hello.Method.returns.to_dict(), ireturns.to_dict())
        self.assertEqual(say_hello.Method.defaults, {})

    def test_returns_not_given_req_or_opt_raises(self):
        with self.assertRaises(AssertionError):
            @returns("hello", StringMeta(), "A default")
            def say_hello(ret):
                """Say hello"""
                ret.hello = "Hello"
                return ret

    def test_only_in(self):
        @only_in("boo", "boo2")
        def f():
            pass

        self.assertTrue(hasattr(f, "Method"))
        self.assertEqual(f.Method.only_in, ("boo", "boo2"))


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/Method:1.0"
        self.takes = MapMeta()
        self.takes.set_elements(OrderedDict({"in_attr": StringMeta("desc")}))
        self.serialized["takes"] = self.takes.to_dict()
        self.serialized["defaults"] = OrderedDict({"in_attr": "default"})
        self.serialized["description"] = "test_description"
        self.serialized["tags"] = []
        self.serialized["writeable"] = True
        self.serialized["label"] = ""
        self.serialized["returns"] = MapMeta().to_dict()

    def test_to_dict(self):
        m = Method("test_description")
        m.set_takes(self.takes)
        m.set_defaults(self.serialized["defaults"])
        self.assertEqual(m.to_dict(), self.serialized)

    def test_from_dict(self):
        m = Method.from_dict(self.serialized.copy())
        self.assertEqual(m.takes.to_dict(), self.takes.to_dict())
        self.assertEqual(m.defaults, self.serialized["defaults"])
        self.assertEqual(m.tags, [])
        self.assertEqual(m.writeable, True)
        self.assertEqual(m.label, "")
        self.assertEqual(m.returns.to_dict(), MapMeta().to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
