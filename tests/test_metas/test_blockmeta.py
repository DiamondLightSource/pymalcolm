import os
import sys
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from malcolm.metas import BlockMeta


class TestInit(unittest.TestCase):
    def test_init(self):
        block_meta = BlockMeta("desc")
        self.assertEqual("malcolm:core/BlockMeta:1.0", block_meta.typeid)

if __name__ == "__main__":
    unittest.main()
