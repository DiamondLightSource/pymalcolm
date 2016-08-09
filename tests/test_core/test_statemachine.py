import os
import sys
import unittest
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.statemachine import StateMachine, DefaultStateMachine, \
    RunnableDeviceStateMachine


class TestStateMachine(unittest.TestCase):
    def test_init_raises_not_implemented(self):
        with self.assertRaises(AssertionError):
            StateMachine("s")


if __name__ == "__main__":
    unittest.main()


class TestDefaultStateMachine(unittest.TestCase):

    def setUp(self):
        self.SM = DefaultStateMachine("test_state_machine")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Resetting'] = {'Ready', 'Fault',
                                                    'Disabled'}
        default_allowed_transitions['Fault'] = {"Resetting", "Disabled"}
        default_allowed_transitions['Disabled'] = {"Resetting"}
        default_allowed_transitions['Ready'] = {"Fault", "Disabled"}

        self.assertEqual("test_state_machine", self.SM.name)
        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)
        self.assertEqual(["Resetting"], self.SM.busy_states)

    def test_is_allowed(self):
        self.SM.allowed_transitions.update(dict(Ready={"Resetting",
                                                       "Rewinding"}))

        response = self.SM.is_allowed("Ready", "Resetting")
        self.assertTrue(response)
        response = self.SM.is_allowed("Ready", "Paused")
        self.assertFalse(response)

    def test_set_allowed(self):
        self.SM.set_allowed("Ready", "Prerun")
        self.assertEqual({"Prerun", "Disabled", "Fault"},
                         self.SM.allowed_transitions['Ready'])
        self.SM.set_allowed("Ready", "Resetting")
        self.assertEqual({"Prerun", "Disabled", "Fault", "Resetting"},
                         self.SM.allowed_transitions['Ready'])

    def test_set_busy(self):
        self.assertEqual(["Resetting"], self.SM.busy_states)
        self.SM.set_busy("Resetting", busy=False)
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=False)
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=True)
        self.assertEqual(["Ready"], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=False)
        self.assertEqual([], self.SM.busy_states)

    def test_is_busy(self):
        self.assertEqual(['Resetting'], self.SM.busy_states)
        response = self.SM.is_busy("Resetting")
        self.assertTrue(response)

        response = self.SM.is_busy("Ready")
        self.assertFalse(response)

    def test_insert(self):

        @DefaultStateMachine.insert
        class DummyController(object):
            pass

        d = DummyController()

        self.assertIsInstance(d.stateMachine, DefaultStateMachine)
        self.assertEqual("DefaultStateMachine", d.stateMachine.name)


class TestRunnableDeviceStateMachine(unittest.TestCase):

    def setUp(self):
        self.SM = RunnableDeviceStateMachine("test_state_machine")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Resetting'] = {"Idle", "Aborting",
                                                    "Fault", "Disabled"}
        default_allowed_transitions['Idle'] = {"Configuring", "Aborting",
                                               "Fault", "Disabled"}
        default_allowed_transitions['Ready'] = {"PreRun", "Rewinding",
                                                "Resetting", "Aborting",
                                                "Fault", "Disabled"}
        default_allowed_transitions['Configuring'] = {"Ready", "Aborting",
                                                      "Fault", "Disabled"}
        default_allowed_transitions['PreRun'] = {"Running", "Rewinding",
                                                 "Aborting", "Fault",
                                                 "Disabled"}
        default_allowed_transitions['Running'] = {"PostRun", "Rewinding",
                                                  "Aborting", "Fault",
                                                  "Disabled"}
        default_allowed_transitions['PostRun'] = {"Idle", "Ready", "Aborting",
                                                  "Fault", "Disabled"}
        default_allowed_transitions['Paused'] = {"Rewinding", "PreRun",
                                                 "Aborting", "Fault",
                                                 "Disabled"}
        default_allowed_transitions['Rewinding'] = {"Paused", "Aborting",
                                                    "Fault", "Disabled"}
        default_allowed_transitions['Aborting'] = {"Aborted", "Fault",
                                                   "Disabled"}
        default_allowed_transitions['Aborted'] = {"Resetting", "Fault",
                                                  "Disabled"}
        default_allowed_transitions['Fault'] = {"Resetting", "Disabled"}
        default_allowed_transitions['Disabled'] = {"Resetting"}

        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)