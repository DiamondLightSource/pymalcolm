#!/bin/env dls-python
import unittest
import sys
import os
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import Mock

from malcolm.core.method import Method

class TestMethod(unittest.TestCase):
    def test_init(self):
        m = Method("test_method")
        self.assertEquals("test_method", m.name)

    def test_simple_function(self):
        func = Mock(return_value = {"first_out":"test"})
        m = Method("test_method")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first":Mock()}
        m.set_function_takes(args_meta)
        result = m(first="test")
        self.assertEquals({"first_out":"test"}, result)
        func.assert_called_with({"first":"test"})

    def test_defaults(self):
        func = Mock(return_value = {"first_out":"test"})
        m = Method("test_method")
        arg_meta = Mock()
        arg_meta.elements = {"first":Mock(), "second":Mock()}
        m.set_function_takes(arg_meta, {"second":"default"})
        m.set_function(func)
        self.assertEquals({"first_out":"test"}, m(first="test"))
        func.assert_called_with({"first":"test", "second":"default"})

    def test_required(self):
        func = Mock(return_value = {"first_out":"test"})
        m = Method("test_method")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first":Mock(), "second":Mock()}
        args_meta.required = ["first"]
        m.set_function_takes(args_meta, {"first":"default"})
        self.assertEquals({"first_out":"test"}, m())
        func.assert_called_with({"first":"default"})

        m.set_function_takes(args_meta, {"second":"default"})
        self.assertRaises(ValueError, m)

    def test_positional_args(self):
        func = Mock(return_value = {"output":2})
        m = Method("test_method")
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
        self.assertEquals({"output":2}, m(2, 3, third=1, fourth=4))
        func.assert_called_with({"first":2, "second":3, "third":1, "fourth":4})

    def test_valid_return(self):
        func = Mock(return_value = {"output1":2, "output2":4})
        m = Method("test_method")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first":Mock(), "second":Mock()}
        args_meta.required = ["first", "second"]
        return_meta = Mock()
        return_meta.elements = {"output1":Mock(), "output2":Mock()}
        validator1 = Mock(return_value=True)
        validator2 = Mock(return_value=True)
        return_meta.elements["output1"].validate = validator1
        return_meta.elements["output2"].validate = validator2
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        self.assertEquals({"output1":2, "output2":4}, m(first=1, second=2))
        func.assert_called_with({"first":1, "second":2})
        validator1.assert_called_with(2)
        validator2.assert_called_with(4)

    def test_incomplete_return(self):
        func = Mock(return_value = {"output1":2})
        m = Method("test_method")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first":Mock(), "second":Mock()}
        return_meta = Mock()
        return_meta.elements = {"output1":Mock(), "output2":Mock()}
        validator = Mock(return_value=True)
        return_meta.elements["output1"].validate = validator
        return_meta.elements["output2"].validate = validator
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        self.assertRaises(ValueError, m, first=1, second=2)
        func.assert_called_with({"first":1, "second":2})

    def test_invalid_return(self):
        func = Mock(return_value = {"output1":2, "output2":4})
        m = Method("test_method")
        m.set_function(func)
        args_meta = Mock()
        args_meta.elements = {"first":Mock(), "second":Mock()}
        return_meta = Mock()
        return_meta.elements = {"output1":Mock(), "output2":Mock()}
        validator1 = Mock(return_value=True)
        validator2 = Mock(side_effect=TypeError("Fake type error"))
        return_meta.elements["output1"].validate = validator1
        return_meta.elements["output2"].validate = validator2
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        self.assertRaises(TypeError, m, first=1, second=2)
        func.assert_called_with({"first":1, "second":2})
        validator2.assert_called_with(4)

    def test_handle_request(self):
        func = Mock(return_value = {"output":1})
        args_meta = Mock(elements = {"first":Mock()})
        return_meta = Mock(elements = {"output":Mock()})
        m = Method("test_method")
        m.set_function(func)
        m.set_function_takes(args_meta)
        m.set_function_returns(return_meta)
        request = Mock(
                id = (123, Mock()), type="Post", parameters = {"first":2},
                respond_with_return = Mock())
        m.handle_request(request)
        func.assert_called_with({"first":2})
        request.respond_with_return.assert_called_with({"output":1})

if __name__ == "__main__":
    unittest.main(verbosity=2)
