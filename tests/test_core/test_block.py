import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, call, patch

# module imports
from malcolm.core.block import Block
from malcolm.core.attribute import Attribute
from malcolm.vmetas import StringMeta
from malcolm.core.methodmeta import MethodMeta
from malcolm.core.request import Post, Put


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block()
        self.assertEqual(list(b.children), [])
        self.assertEqual("malcolm:core/Block:1.0", b.typeid)

    def test_notify(self):
        b = Block()
        b.set_parent(MagicMock(), "n")
        b.notify_subscribers()
        b.parent.notify_subscribers.assert_called_once_with("n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
