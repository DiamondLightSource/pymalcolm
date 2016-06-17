import unittest
import sys
import os
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import Mock, patch, call, MagicMock

from malcolm.core.method import Method, takes, returns
from malcolm.core.mapmeta import OPTIONAL, REQUIRED
from malcolm.core.response import Response


class TestMethod(unittest.TestCase):
    def test_init(self):
        m = Method("test_method", "test_description")
        self.assertEquals("test_method", m.name)
        self.assertEquals("test_description", m.description)

    def test_simple_function(self):
        func = Mock(return_value={"first_out": "test"})
        m = Method("test_method", "test_description")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first": Mock()}
        m.set_function_takes(args_meta)
        result = m(first="test")
        self.assertEquals({"first_out": "test"}, result)
        func.assert_called_with({"first": "test"})

    def test_defaults(self):
        func = Mock(return_value={"first_out": "test"})
        m = Method("test_method", "test_description")
        arg_meta = Mock()
        arg_meta.elements = {"first": Mock(), "second": Mock()}
        m.set_function_takes(arg_meta, {"second": "default"})
        m.set_function(func)
        self.assertEquals({"first_out": "test"}, m(first="test"))
        func.assert_called_with({"first": "test", "second": "default"})

    def test_required(self):
        func = Mock(return_value={"first_out": "test"})
        m = Method("test_method", "test_description")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first": Mock(), "second": Mock()}
        args_meta.required = ["first"]
        m.set_function_takes(args_meta, {"first": "default"})
        self.assertEquals({"first_out": "test"}, m())
        func.assert_called_with({"first": "default"})

        m.set_function_takes(args_meta, {"second": "default"})
        self.assertRaises(ValueError, m)

    def test_positional_args(self):
        func = Mock(return_value={"output": 2})
        m = Method("test_method", "test_description")
        m.set_function(func)
        args_meta = Mock()
        validator = Mock(return_value=True)
        args_meta.elements = OrderedDict()
        args_meta.elements["first"] = Mock(validate=validator)
        args_meta.elements["second"] = Mock(validate=validator)
        args_meta.elements["third"] = Mock(validate=validator)
        args_meta.elements["fourth"] = Mock(validate=validator)
        args_meta.required = ["first", "third"]
        m.set_function_takes(args_meta)
        self.assertEquals({"output": 2}, m(2, 3, third=1, fourth=4))
        func.assert_called_with({"first": 2, "second": 3, "third": 1, "fourth": 4})

    def test_valid_return(self):
        func = Mock(return_value={"output1": 2, "output2": 4})
        m = Method("test_method", "test_description")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first": Mock(), "second": Mock()}
        args_meta.required = ["first", "second"]
        return_meta = Mock()
        return_meta.elements = {"output1": Mock(), "output2": Mock()}
        validator1 = Mock(return_value=True)
        validator2 = Mock(return_value=True)
        return_meta.elements["output1"].validate = validator1
        return_meta.elements["output2"].validate = validator2
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        self.assertEquals({"output1": 2, "output2": 4}, m(first=1, second=2))
        func.assert_called_with({"first": 1, "second": 2})
        validator1.assert_called_with(2)
        validator2.assert_called_with(4)

    def test_incomplete_return(self):
        func = Mock(return_value={"output1": 2})
        m = Method("test_method", "test_description")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first": Mock(), "second": Mock()}
        return_meta = Mock()
        return_meta.elements = {"output1": Mock(), "output2": Mock()}
        validator = Mock(return_value=True)
        return_meta.elements["output1"].validate = validator
        return_meta.elements["output2"].validate = validator
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        self.assertRaises(ValueError, m, first=1, second=2)
        func.assert_called_with({"first": 1, "second": 2})

    def test_invalid_return(self):
        func = Mock(return_value={"output1": 2, "output2": 4})
        m = Method("test_method", "test_description")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first": Mock(), "second": Mock()}
        return_meta = Mock()
        return_meta.elements = {"output1": Mock(), "output2": Mock()}
        validator1 = Mock(return_value=True)
        validator2 = Mock(side_effect=TypeError("Fake type error"))
        return_meta.elements["output1"].validate = validator1
        return_meta.elements["output2"].validate = validator2
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        self.assertRaises(TypeError, m, first=1, second=2)
        func.assert_called_with({"first": 1, "second": 2})
        validator2.assert_called_with(4)

    def test_handle_request(self):
        func = Mock(return_value={"output": 1})
        args_meta = Mock(elements={"first": Mock()})
        return_meta = Mock(elements={"output": Mock()})
        m = Method("test_method", "test_description")
        m.set_function(func)
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        request = Mock(
                id=(123, Mock()), type="Post", parameters={"first": 2},
                respond_with_return=Mock())
        response = m.get_response(request)
        func.assert_called_with({"first": 2})
        self.assertEquals({"output":1}, response.value)

    def test_handle_request_error(self):
        func = MagicMock()
        func.side_effect = ValueError("Test error")
        m = Method("test_method", "test_description")
        m.set_function(func)
        m.takes = MagicMock()
        m.returns = MagicMock()
        request = MagicMock()

        response = m.get_response(request)
        self.assertEquals(Response.ERROR, response.type_)
        self.assertEquals(
            "Method test_method raised an error: Test error", response.message)

    def test_to_dict_serialization(self):
        func = Mock(return_value={"out": "dummy"})
        defaults = {"in_attr": "default"}
        args_meta = Mock(elements={"first": Mock()},
                         to_dict=Mock(
                             return_value=OrderedDict({"dict": "args"})))
        return_meta = Mock(elements={"out": Mock()},
                           to_dict=Mock(
                               return_value=OrderedDict({"dict": "return"})))
        m = Method("test_method", "test_description")
        m.set_function(func)
        m.set_function_takes(args_meta, defaults)
        m.set_function_returns(return_meta)
        expected = OrderedDict()
        expected["description"] = "test_description"
        expected["takes"] = OrderedDict({"dict": "args"})
        expected["defaults"] = OrderedDict({"in_attr": "default"})
        expected["returns"] = OrderedDict({"dict": "return"})
        self.assertEquals(expected, m.to_dict())

    @patch("malcolm.core.method.MapMeta")
    def test_from_dict_deserialize(self, mock_mapmeta):
        name = "foo"
        description = "dummy description"
        takes = dict(a=object(), b=object())
        returns = dict(c=object())
        defaults = dict(a=43)
        d = dict(description=description, takes=takes,
                 returns=returns, defaults=defaults)
        m = Method.from_dict(name, d)
        self.assertEqual(mock_mapmeta.from_dict.call_args_list, [
            call("takes", takes), call("returns", returns)])
        self.assertEqual(m.name, name)
        self.assertEqual(m.takes, mock_mapmeta.from_dict.return_value)
        self.assertEqual(m.returns, mock_mapmeta.from_dict.return_value)
        self.assertEqual(m.defaults, defaults)

    @patch("malcolm.core.method.MapMeta")
    def test_takes_given_optional(self, map_meta_mock):
        m1 = MagicMock()
        map_meta_mock.return_value = m1
        a1 = MagicMock()
        a1.name = "name"

        @takes(a1, OPTIONAL)
        def say_hello(name):
            """Say hello"""
            print("Hello" + name)

        self.assertTrue(hasattr(say_hello, "Method"))
        self.assertEqual(m1, say_hello.Method.takes)
        m1.add_element.assert_called_once_with(a1, False)
        self.assertEqual(0, len(say_hello.Method.defaults))

    @patch("malcolm.core.method.MapMeta")
    def test_takes_given_defaults(self, map_meta_mock):
        m1 = MagicMock()
        map_meta_mock.return_value = m1
        a1 = MagicMock()
        a1.name = "name"

        @takes(a1, "User")
        def say_hello(name):
            """Say hello"""
            print("Hello" + name)

        self.assertTrue(hasattr(say_hello, "Method"))
        self.assertEqual(m1, say_hello.Method.takes)
        m1.add_element.assert_called_once_with(a1, False)
        self.assertEqual("User", say_hello.Method.defaults[a1.name])

    @patch("malcolm.core.method.MapMeta")
    def test_returns_given_valid_sets(self, map_meta_mock):
        m1 = MagicMock()
        map_meta_mock.return_value = m1
        a1 = MagicMock()
        a1.name = "name"

        @returns(a1, REQUIRED)
        def return_hello(name):
            """Return hello"""
            return "Hello" + name

        self.assertTrue(hasattr(return_hello, "Method"))
        self.assertEqual(m1, return_hello.Method.returns)
        m1.add_element.assert_called_once_with(a1, True)

    @patch("malcolm.core.method.MapMeta")
    def test_returns_not_given_req_or_opt_raises(self, _):

        with self.assertRaises(ValueError):
            @returns(MagicMock(), "Raise Error")
            def return_hello(name):
                """Return hello"""
                return "Hello" + name

if __name__ == "__main__":
    unittest.main(verbosity=2)
