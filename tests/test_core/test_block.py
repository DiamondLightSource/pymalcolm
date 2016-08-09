import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, call, patch

# module imports
from malcolm.core.block import Block


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block()
        self.assertEqual(list(b), [])
        self.assertEqual("malcolm:core/Block:1.0", b.typeid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
