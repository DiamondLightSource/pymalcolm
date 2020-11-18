import os
import unittest

from malcolm.modules.builtin.defines import module_path, tmp_dir


class TestModulePath(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(os.path.dirname(__file__), "dummy_module")
        self.d = module_path(name="dummy", path=self.path)

    def tearDown(self):
        import sys

        sys.modules.pop("malcolm.modules.dummy", None)
        import malcolm.modules

        delattr(malcolm.modules, "dummy")

    def test_init(self):
        assert self.d.name == "dummy"
        assert self.d.value == self.path
        import malcolm.modules

        assert hasattr(malcolm.modules, "dummy")
        assert hasattr(malcolm.modules.dummy, "parts")
        assert hasattr(malcolm.modules.dummy.parts, "DummyPart")
        import malcolm.modules.demo

        assert hasattr(malcolm.modules.demo, "parts")
        assert hasattr(malcolm.modules.demo.parts, "HelloPart")


class TestDefines(unittest.TestCase):
    def test_tmp_dir(self):
        d = tmp_dir("config")
        assert d.name == "config"
        assert d.value.startswith("/tmp")
        assert os.path.isdir(d.value)
        os.rmdir(d.value)
