import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, patch

from malcolm.core.part import Part


class TestPart(unittest.TestCase):
    def test_init(self):
        process = Mock()
        block = Mock()
        self.assertRaises(NotImplementedError, Part, "part", process, block,
                                                    None)

    def test_setup(self):
        with patch('malcolm.core.part.Part.__init__') as init_mock:
            init_mock.return_value = None
            p = Part(None, None, None, None)
            self.assertRaises(NotImplementedError, p.setup, None)

if __name__ == "__main__":
    unittest.main(verbosity=2)
