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
            StateMachine("s")


if __name__ == "__main__":
    unittest.main()


class TestDefaultStateMachine(unittest.TestCase):
    def setUp(self):
        self.SM = DefaultStateMachine("test_state_machine")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Reset'] = {'Ready', 'Fault',
                                                    'Disable'}
        default_allowed_transitions['Ready'] = {"Fault", "Disable"}
        default_allowed_transitions['Fault'] = {"Reset", "Disable"}
        default_allowed_transitions['Disable'] = {"Disabled", "Fault"}
        default_allowed_transitions['Disabled'] = {"Reset"}

        self.assertEqual("test_state_machine", self.SM.name)
        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)
        self.assertEqual(["Reset"], self.SM.busy_states)

    def test_is_allowed(self):
        self.SM.allowed_transitions.update(dict(Ready={"Reset",
                                                       "Seeking"}))

        response = self.SM.is_allowed("Ready", "Reset")
        self.assertTrue(response)
        response = self.SM.is_allowed("Ready", "Paused")
        self.assertFalse(response)

    def test_set_allowed(self):
        self.SM.set_allowed("Ready", "Prerun")
        self.assertEqual({"Prerun", "Disable", "Fault"},
                         self.SM.allowed_transitions['Ready'])
        self.SM.set_allowed("Ready", "Reset")
        self.assertEqual({"Prerun", "Disable", "Fault", "Reset"},
                         self.SM.allowed_transitions['Ready'])

    def test_set_busy(self):
        self.assertEqual(["Reset"], self.SM.busy_states)
        self.SM.set_busy("Reset", busy=False)
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=False)
        self.assertEqual([], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=True)
        self.assertEqual(["Ready"], self.SM.busy_states)
        self.SM.set_busy("Ready", busy=False)
        self.assertEqual([], self.SM.busy_states)

    def test_is_busy(self):
        self.assertEqual(['Reset'], self.SM.busy_states)
        response = self.SM.is_busy("Reset")
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


class TestManagerStateMachine(unittest.TestCase):
    def setUp(self):
        self.SM = ManagerStateMachine("test_state_machine")
        self.assertEqual(self.SM.AFTER_RESETTING, "Ready")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Reset'] = {'Ready', 'Fault',
                                                    'Disable'}
        default_allowed_transitions['Ready'] = {
            'Editing', "Fault", "Disable"}
        default_allowed_transitions['Editing'] = {
            'Fault', 'Editable', 'Disable'}
        default_allowed_transitions['Editable'] = {
            'Fault', 'Saving', 'Disable', 'Reverting'}
        default_allowed_transitions['Saving'] = {
            'Fault', 'Ready', 'Disable'}
        default_allowed_transitions['Reverting'] = {
            'Fault', 'Ready', 'Disable'}
        default_allowed_transitions['Fault'] = {"Reset", "Disable"}
        default_allowed_transitions['Disable'] = {"Disabled", "Fault"}
        default_allowed_transitions['Disabled'] = {"Reset"}
        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)


class TestRunnableDeviceStateMachine(unittest.TestCase):
    def setUp(self):
        self.SM = RunnableStateMachine("test_state_machine")
        self.assertEqual(self.SM.AFTER_RESETTING, "Idle")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Reset'] = {
            "Idle", "Abort", "Fault", "Disable"}
        default_allowed_transitions['Idle'] = {
            "Configure", "Abort", 'Editing', "Fault", "Disable"}
        default_allowed_transitions['Editing'] = {
            'Fault', 'Editable', 'Disable'}
        default_allowed_transitions['Editable'] = {
            'Fault', 'Saving', 'Disable', 'Reverting'}
        default_allowed_transitions['Saving'] = {
            'Fault', 'Idle', 'Disable'}
        default_allowed_transitions['Reverting'] = {
            'Fault', 'Idle', 'Disable'}
        default_allowed_transitions['Ready'] = {
            "PreRun", "Seeking", "Reset", "Abort", "Fault", "Disable"}
        default_allowed_transitions['Configure'] = {
            "Ready", "Abort", "Fault", "Disable"}
        default_allowed_transitions['PreRun'] = {
            "Run", "Seeking", "Abort", "Fault", "Disable"}
        default_allowed_transitions['Run'] = {
            "PostRunReady", "Seeking", "Abort", "Fault", "Disable"}
        default_allowed_transitions['PostRunReady'] = {
            "Idle", "Ready", "Abort", "Fault", "Disable"}
        default_allowed_transitions['Paused'] = {
            "Seeking", "PreRun", "Abort", "Fault", "Disable"}
        default_allowed_transitions['Seeking'] = {
            "Paused", "Abort", "Fault", "Disable"}
        default_allowed_transitions['Abort'] = {
            "Aborted", "Fault", "Disable"}
        default_allowed_transitions['Aborted'] = {
            "Reset", "Fault", "Disable"}
        default_allowed_transitions['Fault'] = {"Reset", "Disable"}
        default_allowed_transitions['Disable'] = {"Disabled", "Fault"}
        default_allowed_transitions['Disabled'] = {"Reset"}

        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)
