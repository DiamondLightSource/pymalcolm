import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# import logging
# logging.basicConfig(level=logging.DEBUG)

import setup_malcolm_paths
from mock import MagicMock

# module imports
from malcolm.core.cache import Cache


class TestProcess(unittest.TestCase):

    def test_addition(self):
        c = Cache()
        c.apply_changes([["thing"], {1: 2}])
        self.assertEqual(c["thing"][1], 2)

    def test_deletion(self):
        c = Cache()
        c["path"] = 2
        c.apply_changes([["path"]])
        self.assertEqual(list(c), [])

    def test_change(self):
        c = Cache()
        c[1] = 3
        c.apply_changes([["path"], 4])
        self.assertEqual(c["path"], 4)

    def test_cache_update(self):
        c = Cache()
        c["path"] = 2
        c.apply_changes([[], {123:"test"}])
        self.assertEqual("test", c[123])
        with self.assertRaises(KeyError):
            c["path"]

    def test_non_string_path_errors(self):
        c = Cache()
        self.assertRaises(AssertionError, c.apply_changes, [[1], 3])

    def test_walk_path(self):
        c = Cache()
        c[1] = {2: {3: "end"}}
        walked = c.walk_path([1, 2, 3])
        self.assertEqual(walked, "end")

if __name__ == "__main__":
    unittest.main(verbosity=2)
