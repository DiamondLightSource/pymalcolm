import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.controllers.countercontroller import CounterController


class TestCounterController(unittest.TestCase):
    def test_init(self):
        block = Mock()
        c = CounterController(Mock(), block)
        self.assertIs(block, c.block)
        self.assertEquals(2, len(block.add_method.call_args_list))
        method_1 = block.add_method.call_args_list[0][0][0]
        method_2 = block.add_method.call_args_list[1][0][0]
        self.assertEquals("increment", method_1.name)
        self.assertEquals(c.increment, method_1.func)
        self.assertEquals("reset", method_2.name)
        self.assertEquals(c.reset, method_2.func)

    def test_increment_increments(self):
        c = CounterController(Mock(), Mock())
        self.assertEquals(0, c.counter.value)
        c.increment()
        self.assertEquals(1, c.counter.value)
        c.increment()
        self.assertEquals(2, c.counter.value)

    def test_increment_calls_on_changed(self):
        c = CounterController(Mock(), Mock())
        c.counter.on_changed = Mock(side_effect=c.counter.on_changed)
        c.increment()
        c.counter.on_changed.assert_called_once_with([["value"], 1])

    def test_reset_sets_zero(self):
        c = CounterController(Mock(), Mock())
        c.counter.value = 1234
        c.reset()
        self.assertEquals(0, c.counter.value)

    def test_reset_calls_on_changed(self):
        c = CounterController(Mock(), Mock())
        c.counter.value = 1234
        c.counter.on_changed = Mock(side_effect=c.counter.on_changed)
        c.reset()
        c.counter.on_changed.assert_called_once_with([["value"], 0])

    def test_put_changes_value(self):
        c = CounterController(Mock(), Mock())
        c.counter.parent = c.block
        c.counter.put(32)
        self.assertEqual(c.counter.value, 32)
        c.block.on_changed.assert_called_once_with(
            [["counter", "value"], 32], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
