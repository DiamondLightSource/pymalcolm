import os
import sys
sys.path.append(os.path.dirname(__file__))
import setup_malcolm_paths

import unittest
from mock import Mock, patch, call, MagicMock

from malcolm import parameters
from malcolm.core import REQUIRED
from malcolm.core.vmetas import NumberMeta, StringMeta


class TestParameters(unittest.TestCase):

    def test_imports(self):
        decorated = {}
        for k in dir(parameters):
            v = getattr(parameters, k)
            if hasattr(v, "MethodMeta"):
                decorated[k] = v
        self.assertEqual(decorated, dict(
            string=parameters.string,
            float64=parameters.float64,
            int32=parameters.int32))

    def test_make_string_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        del params.default
        self.assertEqual(list(parameters.string.MethodMeta.takes.elements),
                         ["name", "description", "default"])
        default_meta = parameters.string.MethodMeta.takes.elements["default"]
        self.assertIsInstance(default_meta, StringMeta)
        name, meta, default = parameters.string(params)
        self.assertEqual(default, REQUIRED)
        self.assertEqual(name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, StringMeta)

    def test_make_int32_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32
        default_meta = parameters.int32.MethodMeta.takes.elements["default"]
        self.assertIsInstance(default_meta, NumberMeta)
        self.assertEqual(default_meta.dtype, "int32")
        name, meta, default = parameters.int32(params)
        self.assertEqual(default, 32)
        self.assertEqual(name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, NumberMeta)
        self.assertEqual(meta.dtype, "int32")

    def test_make_float64_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32.6
        name, meta, default = parameters.float64(params)
        self.assertEqual(default, 32.6)
        self.assertEqual(name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, NumberMeta)
        self.assertEqual(meta.dtype, "float64")

if __name__ == "__main__":
    unittest.main(verbosity=2)
