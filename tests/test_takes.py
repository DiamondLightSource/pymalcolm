import setup_malcolm_paths

import unittest
from mock import Mock, patch, call, MagicMock

from malcolm import takes
from malcolm.core.method import REQUIRED
from malcolm.metas import NumberMeta, StringMeta


class TestTakes(unittest.TestCase):

    def test_imports(self):
        decorated = {}
        for k in dir(takes):
            v = getattr(takes, k)
            if hasattr(v, "Method"):
                decorated[k] = v
        self.assertEqual(decorated, dict(
            string=takes.string,
            float64=takes.float64,
            int32=takes.int32))

    def test_make_string_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        del params.default
        self.assertEqual(list(takes.string.Method.takes.elements),
                         ["name", "description", "default"])
        default_meta = takes.string.Method.takes.elements["default"]
        self.assertIsInstance(default_meta, StringMeta)
        meta, default = takes.string(params)
        self.assertEqual(default, REQUIRED)
        self.assertEqual(meta.name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, StringMeta)

    def test_make_int32_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32
        default_meta = takes.int32.Method.takes.elements["default"]
        self.assertIsInstance(default_meta, NumberMeta)
        self.assertEqual(default_meta.dtype, "int32")
        meta, default = takes.int32(params)
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
        meta, default = takes.float64(params)
        self.assertEqual(default, 32.6)
        self.assertEqual(meta.name, "me")
        self.assertEqual(meta.description, "desc")
        self.assertIsInstance(meta, NumberMeta)
        self.assertEqual(meta.dtype, "float64")

if __name__ == "__main__":
    unittest.main(verbosity=2)
