import unittest
import os

from malcolm.core import call_with_params
from malcolm.modules.builtin.defines import module_path


class TestModulePath(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), "dummy_module")
        self.d = call_with_params(module_path, name="dummy", path=self.path)

    def tearDown(self):
        import sys
        sys.modules.pop("malcolm.modules.dummy", None)
        import malcolm.modules
        delattr(malcolm.modules, "dummy")

    def test_init(self):
        assert self.d == {"dummy": self.path}
        import malcolm.modules
        assert hasattr(malcolm.modules, "demo")
        assert hasattr(malcolm.modules.demo, "parts")
        assert hasattr(malcolm.modules.demo.parts, "HelloPart")
        assert hasattr(malcolm.modules, "dummy")
        assert hasattr(malcolm.modules.dummy, "parts")
        assert hasattr(malcolm.modules.dummy.parts, "DummyPart")

