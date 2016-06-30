import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

from collections import OrderedDict

# module imports
from malcolm.core.controller import Controller


class DummyController(Controller):
    def say_hello(self, name):
        print("Hello" + name)
    say_hello.Method = MagicMock()

    def say_goodbye(self, name):
        print("Goodbye" + name)
    say_goodbye.Method = MagicMock()


class TestController(unittest.TestCase):

    def setUp(self):
        b = MagicMock()
        b._methods.values.return_value = ["say_hello", "say_goodbye"]
        self.m1 = MagicMock()
        self.m2 = MagicMock()
        b._methods.__getitem__.side_effect = [self.m1, self.m2]
        self.c = DummyController(b)

    def test_init(self):
        b = MagicMock()
        self.c = DummyController(b)
        self.assertEqual(self.c.block, b)
        b.add_method.assert_has_calls(
            [call(self.c.say_goodbye.Method), call(self.c.say_hello.Method)])

        self.assertEqual(self.c.state.name, "State")
        self.assertEqual(
            self.c.state.meta.typeid, "malcolm:core/ChoiceMeta:1.0")
        self.assertEqual(self.c.status.name, "Status")
        self.assertEqual(self.c.status.meta.typeid, "malcolm:core/String:1.0")
        self.assertEqual(self.c.busy.name, "Busy")
        self.assertEqual(self.c.busy.meta.typeid, "malcolm:core/Boolean:1.0")

        self.assertEqual(OrderedDict(), self.c.writeable_methods)

    def test_transition(self):
        self.c.writeable_methods["Configure"] = "say_hello"
        self.c.stateMachine.allowed_transitions = dict(Idle="Configure")
        self.c.state.value = "Idle"
        self.c.stateMachine.busy_states = ["Configure"]

        self.c.transition("Configure", "Attempting to configure scan...")

        self.assertEqual("Configure", self.c.state.value)
        self.assertEqual("Attempting to configure scan...", self.c.status.value)
        self.assertTrue(self.c.busy.value)
        self.m1.set_writeable.assert_called_once_with(True)
        self.m2.set_writeable.assert_called_once_with(False)

    def test_transition_not_busy(self):
        self.c.writeable_methods["Configure"] = "say_hello"
        self.c.stateMachine.allowed_transitions = dict(Idle="Configure")
        self.c.state.value = "Idle"
        self.c.stateMachine.busy_states = []

        self.c.transition("Configure", "Attempting to configure scan...")

        self.assertFalse(self.c.busy.value)

    def test_transition_raises(self):
        self.c.stateMachine.allowed_transitions = dict(Idle="")
        self.c.state.value = "Idle"

        with self.assertRaises(TypeError):
            self.c.transition("Configure", "Attempting to configure scan...")

    def test_set_writeable_methods(self):
        m = MagicMock()
        m.name = "configure"
        self.c.set_writeable_methods("Idle", [m])

        self.assertEqual(["configure"], self.c.writeable_methods['Idle'])

if __name__ == "__main__":
    unittest.main(verbosity=2)
