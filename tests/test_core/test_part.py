import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.part import Part

class TestPart(unittest.TestCase):
    def test_init(self):
        process = Mock()
        block = Mock()
        p  = Part("part", process, block)
        self.assertIs(process, p.process)
        self.assertIs(block, p.block)
        self.assertEquals("part", p.name)

if __name__ == "__main__":
    unittest.main(verbosity=2)
