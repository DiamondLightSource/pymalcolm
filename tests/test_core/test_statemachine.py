import os
import sys
import unittest
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.statemachine import StateMachine, DefaultStateMachine, \
    ManagerStateMachine, RunnableStateMachine


class TestStateMachine(unittest.TestCase):
    def test_init_raises_not_implemented(self):
        with self.assertRaises(AssertionError):
            StateMachine()


if __name__ == "__main__":
    unittest.main()


class TestDefaultStateMachine(unittest.TestCase):
    def setUp(self):
        self.SM = DefaultStateMachine()

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Resetting'] = {'Ready', 'Fault', 'Disabling'}
        default_allowed_transitions['Ready'] = {"Fault", "Disabling"}
        default_allowed_transitions['Fault'] = {"Resetting", "Disabling"}
        default_allowed_transitions['Disabling'] = {"Disabled", "Fault"}
        default_allowed_transitions['Disabled'] = {"Resetting"}

        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)
        self.assertEqual(["Resetting"], self.SM.busy_states)

    def test_is_allowed(self):
        self.SM.allowed_transitions["Ready"] = {"Resetting", "Seeking"}
        response = self.SM.is_allowed("Ready", "Resetting")
        self.assertTrue(response)
        response = self.SM.is_allowed("Ready", "Paused")
        self.assertFalse(response)

    def test_set_allowed(self):
        self.SM.set_allowed("Ready", "Prerun")
        self.assertEqual({"Prerun", "Disabling", "Fault"},
                         self.SM.allowed_transitions['Ready'])
        self.SM.set_allowed("Ready", "Resetting")
        self.assertEqual({"Prerun", "Disabling", "Fault", "Resetting"},
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


class TestManagerStateMachine(unittest.TestCase):
    def setUp(self):
        self.SM = ManagerStateMachine()
        self.assertEqual(self.SM.AFTER_RESETTING, "Ready")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Resetting'] = {'Ready', 'Fault',
                                                    'Disabling'}
        default_allowed_transitions['Ready'] = {
            'Editable', "Fault", "Disabling"}
        default_allowed_transitions['Editable'] = {
            'Fault', 'Saving', 'Disabling', 'Reverting'}
        default_allowed_transitions['Saving'] = {
            'Fault', 'Ready', 'Disabling'}
        default_allowed_transitions['Reverting'] = {
            'Fault', 'Ready', 'Disabling'}
        default_allowed_transitions['Fault'] = {"Resetting", "Disabling"}
        default_allowed_transitions['Disabling'] = {"Disabled", "Fault"}
        default_allowed_transitions['Disabled'] = {"Resetting"}
        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)


class TestRunnableDeviceStateMachine(unittest.TestCase):
    def setUp(self):
        self.SM = RunnableStateMachine()
        self.assertEqual(self.SM.AFTER_RESETTING, "Idle")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Resetting'] = {
            "Idle", "Fault", "Disabling"}
        default_allowed_transitions['Idle'] = {
            "Configuring", "Aborting", 'Editable', "Fault", "Disabling"}
        default_allowed_transitions['Editable'] = {
            'Fault', 'Saving', 'Disabling', 'Reverting'}
        default_allowed_transitions['Saving'] = {
            'Fault', 'Idle', 'Disabling'}
        default_allowed_transitions['Reverting'] = {
            'Fault', 'Idle', 'Disabling'}
        default_allowed_transitions['Ready'] = {
            "Seeking", "Resetting", "Aborting", "Running", "Fault", "Disabling"}
        default_allowed_transitions['Configuring'] = {
            "Ready", "Aborting", "Fault", "Disabling"}
        default_allowed_transitions['Running'] = {
            "PostRun", "Seeking", "Aborting", "Fault", "Disabling"}
        default_allowed_transitions['PostRun'] = {
            "Idle", "Ready", "Aborting", "Fault", "Disabling"}
        default_allowed_transitions['Paused'] = {
            "Seeking", "Running", "Aborting", "Fault", "Disabling"}
        default_allowed_transitions['Seeking'] = {
            "Ready", "Paused", "Aborting", "Fault", "Disabling"}
        default_allowed_transitions['Aborting'] = {
            "Aborted", "Fault", "Disabling"}
        default_allowed_transitions['Aborted'] = {
            "Resetting", "Fault", "Disabling"}
        default_allowed_transitions['Fault'] = {"Resetting", "Disabling"}
        default_allowed_transitions['Disabling'] = {"Disabled", "Fault"}
        default_allowed_transitions['Disabled'] = {"Resetting"}

        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)
