import unittest

from malcolm.core import Process
from malcolm.modules.demo.blocks import hello_block


class TestHelloBlock(unittest.TestCase):
    def setUp(self):
        self.p = Process("proc")
        for c in hello_block("mri"):
            self.p.add_controller(c)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_say_hello(self):
        b = self.p.block_view("mri")
        expected = "Hello test_name"
        response = b.greet("test_name", 0)
        assert expected == response

    def test_method_meta(self):
        b = self.p.block_view("mri")
        method = b.greet.meta
        assert list(method.to_dict()) == [
            "typeid",
            "takes",
            "defaults",
            "description",
            "tags",
            "writeable",
            "label",
            "returns",
        ]
        assert method.defaults == dict(sleep=0.0)
        assert list(method.takes["elements"]) == ["name", "sleep"]
        assert list(method.returns["elements"]) == ["return"]
        assert method.tags == ["method:return:unpacked"]
        assert method.writeable
