import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

import unittest
from mock import Mock, ANY

from malcolm.parts.demo import CounterPart
from malcolm.core.block import Block


class TestCounterPart(unittest.TestCase):

    def setUp(self):
        self.c = CounterPart(Mock(), None)
        list(self.c.create_attributes())

    def test_increment_increments(self):
        self.assertEquals(0, self.c.counter.value)
        self.c.increment()
        self.assertEquals(1, self.c.counter.value)
        self.c.increment()
        self.assertEquals(2, self.c.counter.value)

    def test_reset_sets_zero(self):
        self.c.counter.set_endpoint_data("value", 1234, notify=False)
        self.c.zero()
        self.assertEquals(0, self.c.counter.value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
