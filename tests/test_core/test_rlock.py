import unittest

from malcolm.core.rlock import RLock
from multiprocessing.pool import ThreadPool
from malcolm.core.spawned import Spawned
from malcolm.core.queue import Queue
from malcolm.core.errors import TimeoutError


def sleep(t):
    try:
        Queue().get(timeout=t)
    except TimeoutError:
        # that's how long we wanted to sleep for
        pass


class TestLockCothread(unittest.TestCase):

    def setUp(self):
        self.pool = ThreadPool(4)
        self.v = None

    def do_spawn(self, func, use_cothread, *args, **kwargs):
        return Spawned(func, args, kwargs, use_cothread, self.pool)

    def do_spawn_unlocked(self, use_cothread):
        l = RLock(use_cothread)

        def set_v1():
            self.v = 1

        # check our setter works in isolation
        self.do_spawn(set_v1, use_cothread).wait()
        self.assertEqual(self.v, 1)

        # now do a long running task works
        with l:
            self.v = 2
            self.assertEqual(self.v, 2)
            self.do_spawn(set_v1, use_cothread).wait()
            self.assertEqual(self.v, 1)

        self.assertEqual(self.v, 1)

    def do_spawn_locked(self, use_cothread):
        l = RLock(use_cothread)

        def set_v1():
            with l:
                self.v = 1

        # check our setter works in isolation
        self.assertEqual(self.v, None)
        self.do_spawn(set_v1, use_cothread).wait()
        self.assertEqual(self.v, 1)

        # now do a long running task works
        with l:
            self.v = 2
            self.assertEqual(self.v, 2)
            # start our thing that will be blocked, then sleep to make sure
            # it can't do its thing
            s = self.do_spawn(set_v1, use_cothread)
            sleep(0.2)
            self.assertEqual(self.v, 2)

        # now wait for the other to complete, and check it could
        s.wait()
        self.assertEqual(self.v, 1)

    def test_allowed_unlocked_threads_cothread(self):
        self.do_spawn_unlocked(True)

    def test_allowed_unlocked_threads_no_cothread(self):
        self.do_spawn_unlocked(False)

    def test_locked_threads_not_allowed_cothread(self):
        self.do_spawn_locked(True)

    def test_locked_threads_not_allowed_no_cothread(self):
        self.do_spawn_locked(False)
