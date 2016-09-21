import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.controllers.managercontroller import ManagerController
from malcolm.core import method_only_in, method_takes, DefaultStateMachine


class TestManagerController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.c = ManagerController('block', MagicMock())
        self.b = self.c.block




if __name__ == "__main__":
    unittest.main(verbosity=2)
