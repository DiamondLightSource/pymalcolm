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
        b.methods.values.return_value = ["say_hello", "say_goodbye"]
        self.m1 = MagicMock()
        self.m2 = MagicMock()
        b.methods.__getitem__.side_effect = [self.m1, self.m2]
        self.c = DummyController(MagicMock(), b)

    def test_init(self):
        self.c.process.add_block.assert_called_once_with(self.c.block)
        self.c.block.add_method.assert_has_calls(
            [call(self.c.say_goodbye.Method), call(self.c.say_hello.Method)])
        self.assertEqual([], self.c.parts)

        self.assertEqual(self.c.state.name, "State")
        self.assertEqual(
            self.c.state.meta.typeid, "malcolm:core/ChoiceMeta:1.0")
        self.assertEqual(self.c.status.name, "Status")
        self.assertEqual(
            self.c.status.meta.typeid, "malcolm:core/StringMeta:1.0")
        self.assertEqual(self.c.busy.name, "Busy")
        self.assertEqual(
            self.c.busy.meta.typeid, "malcolm:core/BooleanMeta:1.0")

        self.assertEqual(OrderedDict(), self.c.writeable_methods)

    def test_transition(self):
        self.c.reset()
        self.b.busy.set_value.assert_has_calls([call(True), call(False)])
        self.b.state.set_value.assert_has_calls([call("Resetting"), call("Ready")])
        self.b.status.set_value.assert_has_calls([
            call("Resetting"), call("Done resetting")])
        self.c.disable()
        self.assertEqual(self.c.state.value, "Disabled")

    def test_transition_raises(self):
        self.c.stateMachine.allowed_transitions = dict(Idle="")
        self.c.state.value = "Idle"

        with self.assertRaises(TypeError):
            self.c.transition("Configure", "Attempting to configure scan...")

    def test_reset_fault(self):
        self.c.Resetting = MagicMock()
        self.c.Resetting.run.side_effect = ValueError("boom")
        self.c.reset()
        self.b.busy.set_value.assert_has_calls([call(True), call(False)])
        self.b.state.set_value.assert_has_calls([call("Resetting"), call("Fault")])
        self.b.status.set_value.assert_has_calls([
            call("Resetting"), call("boom")])


    def test_set_writeable_methods(self):
        m = MagicMock()
        m.name = "configure"
        self.c.set_writeable_methods("Idle", [m])

        self.assertEqual(["configure"], self.c.writeable_methods['Idle'])

    def test_add_part(self):
        parts = [MagicMock(), MagicMock()]
        self.c.add_parts(parts)
        self.assertEqual(parts, self.c.parts)

if __name__ == "__main__":
    unittest.main(verbosity=2)
