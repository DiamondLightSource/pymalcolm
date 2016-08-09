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
from malcolm.core.controller import Controller, DefaultStateMachine
from malcolm.core.methodmeta import only_in, method_takes


class DummyController(Controller):
    @method_takes()
    def say_hello(self, name):
        print("Hello" + name)

    @only_in("Ready")
    def say_goodbye(self, name):
        print("Goodbye" + name)


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.c = DummyController('block', MagicMock())
        self.b = self.c.block
        for attr in ["busy", "state", "status"]:
            attr = self.b[attr]
            attr.set_value = MagicMock(side_effect=attr.set_value)

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
        disable = self.b["disable"]
        reset = self.b["reset"]
        say_hello = self.b["say_hello"]
        say_goodbye = self.b["say_goodbye"]
        expected = dict(
            Disabled={disable: False, reset: True, say_hello: False, say_goodbye: False},
            Fault={disable: True, reset: True, say_hello: True, say_goodbye: False},
            Ready={disable: True, reset: False, say_hello: True, say_goodbye: True},
            Resetting={disable: True, reset: False, say_hello: True, say_goodbye: False},
        )

        self.assertEqual(expected, self.c.methods_writeable)

    def test_transition(self):
        self.c.reset()
        self.b["busy"].set_value.assert_has_calls([
            call(True, notify=False), call(False, notify=False)])
        self.b["status"].set_value.assert_has_calls([
            call("Resetting", notify=False), call("Done resetting", notify=False)])
        self.b["state"].set_value.assert_has_calls([
            call("Resetting", notify=False), call("Ready", notify=False)])
        self.c.disable()
        self.assertEqual(self.c.state.value, "Disabled")

    def test_transition_raises(self):
        self.c.state.set_value("Ready")

        with self.assertRaises(TypeError):
            self.c.transition("Configuring", "Attempting to configure scan...")

    def test_reset_fault(self):
        self.c.Resetting = MagicMock()
        self.c.Resetting.run.side_effect = ValueError("boom")
        self.c.reset()
        self.b["busy"].set_value.assert_has_calls(
            [call(True, notify=False), call(False, notify=False)])
        self.b["state"].set_value.assert_has_calls(
            [call("Resetting", notify=False), call("Fault", notify=False)])
        self.b["status"].set_value.assert_has_calls(
            [call("Resetting", notify=False), call("boom", notify=False)])

    def test_set_writeable_methods(self):
        m = MagicMock()
        m.name = "configure"
        self.c.register_method_writeable(m, "Ready")
        self.assertEqual(self.c.methods_writeable['Ready'][m], True)

    def test_create_methods_order(self):
        expected = ["disable", "reset", "say_goodbye", "say_hello"]
        actual = list(aname for aname, _, _ in self.c.create_methods())
        self.assertEqual(expected, actual)

if __name__ == "__main__":
    unittest.main(verbosity=2)
