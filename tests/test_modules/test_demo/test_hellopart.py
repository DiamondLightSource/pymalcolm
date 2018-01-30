import unittest

from malcolm.core import Process
from malcolm.modules.builtin.controllers import BasicController
from malcolm.modules.demo.parts import HelloPart


class TestHelloPart(unittest.TestCase):

    def setUp(self):
        self.p = Process("proc")
        c = BasicController("mri")
        c.add_part(HelloPart(name='block'))
        self.p.add_controller(c)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_say_hello(self):
        b = self.p.block_view("mri")
        expected = "Hello test_name"
        response = b.greet("test_name", 0)
        assert expected == response
