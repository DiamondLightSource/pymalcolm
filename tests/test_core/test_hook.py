import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, patch, call
from collections import OrderedDict

from malcolm.core.hook import Hook, get_hook_decorated
from malcolm.core.vmetas import StringMeta, StringArrayMeta
from malcolm.core import method_returns, REQUIRED


class DummyController(object):

    Configuring = Hook()
    Running = Hook()


class DummyPart1(object):

    @DummyController.Configuring
    def do_thing(self, task):
        pass

    @DummyController.Running
    @method_returns(
        "foo", StringMeta("Value of foo"), REQUIRED,
        "bar", StringMeta("Value of bar"), REQUIRED)
    def do_the_other_thing(self, task, returns):
        returns.foo = "foo1"
        returns.bar = "bar2"
        return returns


class DummyPart2(object):

    @DummyController.Configuring
    def do_all_the_things(self):
        pass


class TestHook(unittest.TestCase):

    def test_decorator(self):
        self.assertEqual(type(DummyPart1().do_thing.Hook), Hook)

    def setUp(self):
        block_mock = MagicMock()
        block_mock.name = "TestBlock"
        self.c = DummyController()
        self.c.block = block_mock

    def test_get_hook_decorated(self):
        inst = DummyPart1()
        decorated = list(get_hook_decorated(inst))
        self.assertEqual(decorated, [
            ("do_the_other_thing", DummyController.Running, inst.do_the_other_thing),
            ("do_thing", DummyController.Configuring, inst.do_thing)])

    def test_find_func_tasks(self):
        inst1 = DummyPart1()
        inst2 = DummyPart2()
        part_tasks = {inst1: MagicMock(), inst2: MagicMock()}
        func_tasks = DummyController().Configuring.find_func_tasks(part_tasks)
        self.assertEqual(func_tasks, {
                         inst1.do_thing: part_tasks[inst1],
                         inst2.do_all_the_things: part_tasks[inst2]})

    def test_make_return_table(self):
        inst1 = DummyPart1()
        inst2 = DummyPart2()
        part_tasks = {inst1: MagicMock(), inst2: MagicMock()}
        table_meta = DummyController().Running.make_return_table(part_tasks)
        self.assertEqual(list(table_meta.endpoints), ["name", "foo", "bar"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
