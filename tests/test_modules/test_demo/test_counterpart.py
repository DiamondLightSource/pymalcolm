import unittest

from malcolm.core import Process
from malcolm.modules.builtin.controllers import BasicController
from malcolm.modules.demo.parts import CounterPart


class TestCounterPart(unittest.TestCase):

    def setUp(self):
        self.p = Process("proc")
        c = BasicController("mri")
        c.add_part(CounterPart(name='counting'))
        self.p.add_controller(c)
        self.p.start()
        self.b = self.p.block_view("mri")

    def tearDown(self):
        self.p.stop()

    def test_increment_increments(self):
        assert 0 == self.b.counter.value
        self.b.increment()
        assert 1 == self.b.counter.value
        self.b.increment()
        assert 2 == self.b.counter.value

    def test_reset_sets_zero(self):
        self.b.counter.put_value(1234)
        assert 1234 == self.b.counter.value
        self.b.zero()
        assert 0 == self.b.counter.value
