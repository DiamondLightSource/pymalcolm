import unittest

from annotypes import NO_DEFAULT

from malcolm.modules.builtin import parameters


class TestParameters(unittest.TestCase):
    def test_imports(self):
        decorated = {}
        for k in dir(parameters):
            v = getattr(parameters, k)
            if hasattr(v, "call_types"):
                decorated[k] = v
        assert decorated == dict(
            string=parameters.string, float64=parameters.float64, int32=parameters.int32
        )

    def test_make_string(self):
        o = parameters.string("me", "desc")
        assert o.default == NO_DEFAULT
        assert o.typ is str
        assert o.name == "me"
        assert o.description == "desc"

    def test_make_int32(self):
        o = parameters.int32("me", "desc", 32)
        assert o.default == 32
        assert o.typ is int
        assert o.name == "me"
        assert o.description == "desc"

    def test_make_float64(self):
        o = parameters.float64("me", "desc", 32.6)
        assert o.default == 32.6
        assert o.typ is float
        assert o.name == "me"
        assert o.description == "desc"
