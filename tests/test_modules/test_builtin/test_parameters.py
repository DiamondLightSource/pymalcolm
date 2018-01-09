import unittest
from mock import Mock

from malcolm.modules.builtin import parameters
from malcolm.core import REQUIRED
from malcolm.core.vmetas import NumberMeta, StringMeta


class TestParameters(unittest.TestCase):

    def test_imports(self):
        decorated = {}
        for k in dir(parameters):
            v = getattr(parameters, k)
            if hasattr(v, "MethodModel"):
                decorated[k] = v
        assert decorated == dict(
            string=parameters.string,
            float64=parameters.float64,
            int32=parameters.int32)

    def test_make_string_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        del params.default
        assert list(parameters.string.MethodModel.takes.elements) == (
                         ["name", "description", "default"])
        default_meta = parameters.string.MethodModel.takes.elements["default"]
        self.assertIsInstance(default_meta, StringMeta)
        name, meta, default = parameters.string(params)
        assert default == REQUIRED
        assert name == "me"
        assert meta.description == "desc"
        self.assertIsInstance(meta, StringMeta)

    def test_make_int32_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32
        default_meta = parameters.int32.MethodModel.takes.elements["default"]
        self.assertIsInstance(default_meta, NumberMeta)
        assert default_meta.dtype == "int32"
        name, meta, default = parameters.int32(params)
        assert default == 32
        assert name == "me"
        assert meta.description == "desc"
        self.assertIsInstance(meta, NumberMeta)
        assert meta.dtype == "int32"

    def test_make_float64_meta(self):
        params = Mock()
        params.name = "me"
        params.description = "desc"
        params.default = 32.6
        name, meta, default = parameters.float64(params)
        assert default == 32.6
        assert name == "me"
        assert meta.description == "desc"
        self.assertIsInstance(meta, NumberMeta)
        assert meta.dtype == "float64"
