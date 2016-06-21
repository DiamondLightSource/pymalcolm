import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.runnabledevicestatemachine import RunnableDeviceStateMachine


class TestRunnableDeviceStateMachine(unittest.TestCase):

    def setUp(self):
        self.SM = RunnableDeviceStateMachine("test_state_machine")

    def test_init(self):
        default_allowed_transitions = OrderedDict()
        default_allowed_transitions['Fault'] = ["Resetting", "Disabled"]
        default_allowed_transitions['Disabled'] = ["Resetting"]
        default_allowed_transitions['Idle'] = ["Configuring", "Aborting"]
        default_allowed_transitions['Ready'] = ["PreRun", "Rewinding",
                                                "Resetting", "Aborting"]
        default_allowed_transitions['Configuring'] = ["Ready", "Aborting"]
        default_allowed_transitions['PreRun'] = ["Running", "Rewinding",
                                                 "Aborting"]
        default_allowed_transitions['Running'] = ["PostRun", "Rewinding",
                                                  "Aborting"]
        default_allowed_transitions['PostRun'] = ["Idle", "Ready", "Aborting"]
        default_allowed_transitions['Resetting'] = ["Idle", "Aborting"]
        default_allowed_transitions['Paused'] = ["Rewinding", "PreRun", "Aborting"]
        default_allowed_transitions['Rewinding'] = ["Paused", "Aborting"]
        default_allowed_transitions['Aborting'] = ["Aborted"]
        default_allowed_transitions['Aborted'] = ["Resetting"]

        self.assertEqual(default_allowed_transitions,
                         self.SM.allowed_transitions)

if __name__ == "__main__":
    unittest.main(verbosity=2)
