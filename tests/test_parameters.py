import setup_malcolm_paths

import unittest
from mock import Mock, patch, call, MagicMock

from malcolm import parameters
from malcolm.core.method import REQUIRED
from malcolm.metas import NumberMeta, StringMeta


class TestParameters(unittest.TestCase):

    def test_imports(self):
        decorated = {}
        for k in dir(parameters):
            v = getattr(parameters, k)
            if hasattr(v, "Method"):
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
        self.assertEqual(list(parameters.string.Method.takes.elements),
                         ["name", "description", "default"])
        default_meta = parameters.string.Method.takes.elements["default"]
        self.assertIsInstance(default_meta, StringMeta)
        meta, default = parameters.string(params)
        self.assertEqual(default, REQUIRED)
        self.assertEqual(meta.name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, StringMeta)

    def test_make_int32_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32
        default_meta = parameters.int32.Method.takes.elements["default"]
        self.assertIsInstance(default_meta, NumberMeta)
        self.assertEqual(default_meta.dtype, "int32")
        meta, default = parameters.int32(params)
        self.assertEqual(default, 32)
        self.assertEqual(meta.name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, NumberMeta)
        self.assertEqual(meta.dtype, "int32")

    def test_make_float64_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32.6
        meta, default = parameters.float64(params)
        self.assertEqual(default, 32.6)
        self.assertEqual(meta.name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, NumberMeta)
        self.assertEqual(meta.dtype, "float64")

if __name__ == "__main__":
    unittest.main(verbosity=2)
