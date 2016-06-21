import unittest
from collections import OrderedDict
# import logging
# logging.basicConfig(level=logging.DEBUG)

from . import util
from mock import MagicMock

# module imports
from malcolm.core.cache import Cache


class TestProcess(unittest.TestCase):

    def test_addition(self):
        c = Cache()
        c.delta_update([["thing"], {1: 2}])
        self.assertEqual(c["thing"][1], 2)

    def test_deletion(self):
        c = Cache()
        c[1] = 2
        c.delta_update([[1]])
        self.assertEqual(list(c), [])

    def test_change(self):
        c = Cache()
        c[1] = 3
        c.delta_update([[1], 4])
        self.assertEqual(c[1], 4)

    def test_update_root_errors(self):
        c = Cache()
        self.assertRaises(AssertionError, c.delta_update, [[], 3])

    def test_walkt_path(self):
        c = Cache()
        c[1] = {2: {3: "end"}}
        walked = c.walk_path([1, 2, 3])
        self.assertEqual(walked, "end")
