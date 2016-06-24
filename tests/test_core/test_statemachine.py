import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.statemachine import StateMachine

class TestStateMachine(unittest.TestCase):
    def test_init_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            s = StateMachine("s")

if __name__ == "__main__":
    unittest.main()
