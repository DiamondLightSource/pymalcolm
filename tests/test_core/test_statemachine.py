import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.statemachine import StateMachine


class TestStateMachine(unittest.TestCase):

    def setUp(self):
        self.SM = StateMachine("test_state_machine")

    def test_init(self):
        self.assertEqual("test_state_machine", self.SM.name)
        self.assertEqual(OrderedDict(), self.SM.allowed_transitions)
        self.assertEqual([], self.SM.busy_states)

    def test_is_allowed(self):
        self.SM.allowed_transitions.update(dict(Ready=["Resetting",
                                                       "Rewinding"]))

        response = self.SM.is_allowed("Ready", "Resetting")
        self.assertTrue(response)
        response = self.SM.is_allowed("Ready", "Paused")
        self.assertFalse(response)

    def test_set_allowed(self):
        self.SM.set_allowed("Ready", "Prerun")
        self.assertEqual(["Prerun"], self.SM.allowed_transitions['Ready'])
        self.SM.set_allowed("Ready", "Resetting")
        self.assertEqual(["Prerun", "Resetting"], self.SM.allowed_transitions['Ready'])

    def test_set_busy(self):
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=False)
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=True)
        self.assertEqual(["Ready"], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=False)
        self.assertEqual([], self.SM.busy_states)

    def test_is_busy(self):
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Resetting", busy=True)

        response = self.SM.is_busy("Resetting")
        self.assertTrue(response)

        response = self.SM.is_busy("Ready")
        self.assertFalse(response)

    def test_insert(self):

        @StateMachine.insert
        class DummyController(object):
            pass

        d = DummyController()

        self.assertIsInstance(d.stateMachine, StateMachine)
        self.assertEqual("StateMachine", d.stateMachine.name)
