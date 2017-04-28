import unittest

from malcolm.modules.demo.parts import CounterPart
from malcolm.core import call_with_params


class TestCounterPart(unittest.TestCase):

    def setUp(self):
        self.c = call_with_params(CounterPart, name="counting")
        list(self.c.create_attributes())

    def test_increment_increments(self):
        assert 0 == self.c.counter.value
        self.c.increment()
        assert 1 == self.c.counter.value
        self.c.increment()
        assert 2 == self.c.counter.value

    def test_reset_sets_zero(self):
        self.c.counter.set_value(1234)
        self.c.zero()
        assert 0 == self.c.counter.value
