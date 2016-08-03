import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

import unittest
from mock import Mock, ANY

from malcolm.controllers.countercontroller import CounterController
from malcolm.core.block import Block


class TestCounterController(unittest.TestCase):

    def test_increment_increments(self):
        c = CounterController('block', Mock())
        self.assertEquals(0, c.counter.value)
        c.increment()
        self.assertEquals(1, c.counter.value)
        c.increment()
        self.assertEquals(2, c.counter.value)

    def test_increment_calls_on_changed(self):
        c = CounterController('block', Mock())
        c.counter.report_changes = Mock(side_effect=c.counter.report_changes)
        c.increment()
        c.counter.report_changes.assert_called_once_with(
            [['counter', 'value'], 1])

    def test_reset_sets_zero(self):
        c = CounterController('block', Mock())
        c.counter.value = 1234
        c.do_reset()
        self.assertEquals(0, c.counter.value)

if __name__ == "__main__":
    unittest.main(verbosity=2)
