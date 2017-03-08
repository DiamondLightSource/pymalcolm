import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import patch
from cothread import Spawn, Yield

# module imports
from malcolm.core.rlock import RLock


class TestLockCothread(unittest.TestCase):

    def setUp(self):
        self.o = RLock()
        self.v = None

    def test_lock_allows_other_unlocked_cothreads(self):
        def set_v1():
            self.v = 1

        # check our setter works in isolation
        Spawn(set_v1).Wait()
        self.assertEqual(self.v, 1)

        # now do a long running task works
        with self.o:
            self.v = 2
            self.assertEqual(self.v, 2)
            Spawn(set_v1).Wait()
            self.assertEqual(self.v, 1)

        self.assertEqual(self.v, 1)

    def test_locked_blocks_other_cothreads(self):
        def set_v1():
            with self.o:
                self.v = 1

        # check our setter works in isolation
        self.assertEqual(self.v, None)
        Spawn(set_v1).Wait()
        self.assertEqual(self.v, 1)

        # now do a long running task works
        with self.o:
            self.v = 2
            self.assertEqual(self.v, 2)
            # start our thing that will be blocked, then yield to make sure
            # it can't set our variable
            Spawn(set_v1)
            Yield()
            Yield()
            Yield()
            self.assertEqual(self.v, 2)

        self.assertEqual(self.v, 2)
        # let the other cothread get a lookin
        Yield()
        self.assertEqual(self.v, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
