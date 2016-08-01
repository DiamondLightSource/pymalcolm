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
    def test_init(self):
        block = Block()
        block.add_method = Mock(wraps=block.add_method)
        c = CounterController(Mock(), block, 'block')
        self.assertIs(block, c.block)
        self.assertEquals(3, len(block.add_method.call_args_list))
        method_1 = block.add_method.call_args_list[0][0][1]
        method_2 = block.add_method.call_args_list[1][0][1]
        method_3 = block.add_method.call_args_list[2][0][1]
        self.assertEquals("disable", method_1.name)
        self.assertEquals(c.disable, method_1.func)
        self.assertEquals("increment", method_2.name)
        self.assertEquals(c.increment, method_2.func)
        self.assertEquals("reset", method_3.name)
        self.assertEquals(c.reset, method_3.func)

    def test_increment_increments(self):
        c = CounterController(Mock(), Block(), 'block')
        self.assertEquals(0, c.counter.value)
        c.increment()
        self.assertEquals(1, c.counter.value)
        c.increment()
        self.assertEquals(2, c.counter.value)

    def test_increment_calls_on_changed(self):
        c = CounterController(Mock(), Block(), 'block')
        c.counter.on_changed = Mock(side_effect=c.counter.on_changed)
        c.increment()
        c.counter.on_changed.assert_called_once_with(
            [['counter', 'value'], 1], True)

    def test_reset_sets_zero(self):
        c = CounterController(Mock(), Block(), 'c')
        c.counter.value = 1234
        c.do_reset()
        self.assertEquals(0, c.counter.value)

    def add_method(self, name, method):
        method.name = name

    def test_put_changes_value(self):
        b = Block()
        b.on_changed = Mock(wraps=b.on_changed)
        c = CounterController(Mock(), b, 'block')
        b.on_changed.reset_mock()
        c.counter.put(32)
        self.assertEqual(c.counter.value, 32)
        c.block.on_changed.assert_called_once_with(
            [["counter", "value"], 32], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
