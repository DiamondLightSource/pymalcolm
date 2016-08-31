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
from malcolm.controllers.builtin import ManagerController
from malcolm.core import method_only_in, method_takes, DefaultStateMachine


def iterator():
    i = 1
    while i <= 10:
        yield i
        i += 1


class TestManagerController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.c = ManagerController('block', MagicMock())
        self.b = self.c.block

    def test_get_point(self):
        self.c.iterator = iterator()
        self.c.points = []
        self.assertEqual(self.c.get_point(0), 1)
        self.assertEqual(self.c.get_point(5), 6)
        self.assertEqual(self.c.get_point(3), 4)
        self.assertRaises(StopIteration, self.c.get_point, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
