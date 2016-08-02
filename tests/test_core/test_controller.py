import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

from collections import OrderedDict

# module imports
from malcolm.core.controller import Controller
from malcolm.core.block import Block


class DummyController(Controller):
    def say_hello(self, name):
        print("Hello" + name)
    say_hello.Method = MagicMock(only_in=None)
    say_hello.Method.name = "say_hello"

    def say_goodbye(self, name):
        print("Goodbye" + name)
    say_goodbye.Method = MagicMock(only_in=["Ready"])
    say_goodbye.Method.name = "say_goodbye"


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.b = Block()
        self.b.name = "block"
        self.c = DummyController(MagicMock(), self.b, 'block')
        for attr in ["busy", "state", "status"]:
            attr = self.b.attributes[attr]
            attr.set_value = MagicMock(side_effect=attr.set_value)

    def test_init(self):
        self.c.process.add_block.assert_called_once_with("block", self.b)
        self.assertEqual(self.b.methods["say_hello"], self.c.say_hello.Method)
        self.assertEqual(self.b.methods["say_goodbye"], self.c.say_goodbye.Method)
        self.assertEqual([], self.c.parts)

        self.assertEqual(self.c.state.name, "state")
        self.assertEqual(
            self.c.state.meta.typeid, "malcolm:core/ChoiceMeta:1.0")
        self.assertEqual(self.c.state.value, "Disabled")
        self.assertEqual(self.c.status.name, "status")
        self.assertEqual(
            self.c.status.meta.typeid, "malcolm:core/StringMeta:1.0")
        self.assertEqual(self.c.status.value, "Disabled")
        self.assertEqual(self.c.busy.name, "busy")
        self.assertEqual(
            self.c.busy.meta.typeid, "malcolm:core/BooleanMeta:1.0")
        self.assertEqual(self.c.busy.value, False)
        expected = dict(
            Disabled=dict(disable=False, reset=True, say_hello=False, say_goodbye=False),
            Fault=dict(disable=True, reset=True, say_hello=True, say_goodbye=False),
            Ready=dict(disable=True, reset=False, say_hello=True, say_goodbye=True),
            Resetting=dict(disable=True, reset=False, say_hello=True, say_goodbye=False),
        )

        self.assertEqual(expected, self.c.methods_writeable)

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
            self.c.transition("Configuring", "Attempting to configure scan...")

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
        self.c.set_method_writeable_in(m, "Ready")

        self.assertEqual(self.c.methods_writeable['Ready']["configure"], True)

    def test_add_part(self):
        parts = [MagicMock(), MagicMock()]
        self.c.add_parts(parts)
        self.assertEqual(parts, self.c.parts)

    def test_create_methods_order(self):
        expected = ["disable", "reset", "say_goodbye", "say_hello"]
        actual = list(aname for aname, _ in self.c.create_methods())
        self.assertEqual(expected, actual)

if __name__ == "__main__":
    unittest.main(verbosity=2)
