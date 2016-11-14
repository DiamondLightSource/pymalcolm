import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.core.syncfactory import SyncFactory
from malcolm.core import Process

class TestRunnableChildPart(unittest.TestCase):

    def setUp(self):
        # code coverage is currently provided via TestRunnableController
        pass

    def test_init(self):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)