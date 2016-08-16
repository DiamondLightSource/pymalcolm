import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.controller import Controller


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.c = Controller('block', MagicMock())
        self.b = self.c.block

    def test_init(self):
        self.c.process.add_block.assert_called_once_with(self.b)
        self.assertEqual({}, self.c.parts)

        self.assertEqual(
            self.b["state"].meta.typeid, "malcolm:core/ChoiceMeta:1.0")
        self.assertEqual(self.b.state, "Disabled")
        self.assertEqual(
            self.b["status"].meta.typeid, "malcolm:core/StringMeta:1.0")
        self.assertEqual(self.b.status, "Disabled")
        self.assertEqual(
            self.b["busy"].meta.typeid, "malcolm:core/BooleanMeta:1.0")
        self.assertEqual(self.b.busy, False)

    def test_set_writeable_methods(self):
        m = MagicMock()
        m.name = "configure"
        self.c.register_method_writeable(m, "Ready")
        self.assertEqual(self.c.methods_writeable['Ready'][m], True)

    def test_run_hook(self):
        hook = MagicMock()
        func = MagicMock()
        task = MagicMock()
        part = MagicMock()
        hook_tasks = {func:task}
        part_tasks = {part:task}
        hook_queue = self.c.process.create_queue.return_value
        hook_queue.get.return_value = (func, func.return_value)
        hook.find_func_tasks.return_value = {func:task}
        self.c.test_hook = hook
        self.c.hook_names = {hook:"test_hook"}
        self.c.parts = {"test_part":part}
        result = self.c.run_hook(hook, part_tasks)

        # TODO: would like this assertion - difficult to test with mocks
        #hook_queue.put.assert_called_once_with((func, func.return_value))
        self.assertEquals({"test_part":func.return_value}, result)

    def test_run_hook_raises(self):
        hook = MagicMock()
        func = MagicMock(side_effect=Exception("Test Exception"))
        task = MagicMock()
        part = MagicMock()
        hook_tasks = {func:task}
        part_tasks = {part:task}
        hook_queue = self.c.process.create_queue.return_value
        hook_queue.get.return_value = (func, func.side_effect)
        hook.find_func_tasks.return_value = {func:task}
        self.c.test_hook = hook
        self.c.hook_names = {hook:"test_hook"}
        self.c.parts = {"test_part":part}

        with self.assertRaises(Exception) as cm:
            self.c.run_hook(hook, part_tasks)
        self.assertIs(func.side_effect, cm.exception)
        #TODO: test hook_queue.put/get mechanism

if __name__ == "__main__":
    unittest.main(verbosity=2)
