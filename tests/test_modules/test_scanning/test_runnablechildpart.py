import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest


# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports

class TestRunnableChildPart(unittest.TestCase):

    def setUp(self):
        # code coverage is currently provided via TestRunnableController
        pass

    def test_init(self):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)