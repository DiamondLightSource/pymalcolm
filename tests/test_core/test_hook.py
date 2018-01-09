import unittest
from mock import MagicMock

from malcolm.core.hook import Hook, get_hook_decorated
from malcolm.core.vmetas import StringMeta
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
        assert (
            DummyPart1().do_thing.Hooked) == [DummyController.Configuring]

    def setUp(self):
        block_mock = MagicMock()
        block_mock.name = "TestBlock"
        self.c = DummyController()
        self.c.block = block_mock

    def test_get_hook_decorated(self):
        inst = DummyPart1()
        decorated = list(get_hook_decorated(inst))
        assert decorated == [
            ("do_the_other_thing", DummyController.Running, inst.do_the_other_thing),
            ("do_thing", DummyController.Configuring, inst.do_thing)]
