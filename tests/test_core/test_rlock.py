import unittest

from malcolm.core import Queue, RLock, Spawned, TimeoutError


def sleep(t):
    try:
        Queue().get(timeout=t)
    except TimeoutError:
        # that's how long we wanted to sleep for
        pass


class TestLockCothread(unittest.TestCase):
    def setUp(self):
        self.v = None

    def do_spawn(self, func, *args, **kwargs):
        return Spawned(func, args, kwargs)

    def test_spawn_unlocked(self):
        lock = RLock()

        def set_v1():
            self.v = 1

        # check our setter works in isolation
        self.do_spawn(set_v1).wait()
        assert self.v == 1

        # now do a long running task works
        with lock:
            self.v = 2
            assert self.v == 2
            self.do_spawn(set_v1).wait()
            assert self.v == 1

        assert self.v == 1

    def test_spawn_locked(self):
        lock = RLock()

        def set_v1():
            with lock:
                self.v = 1

        # check our setter works in isolation
        assert self.v is None
        self.do_spawn(set_v1).wait()
        assert self.v == 1

        # now do a long running task works
        with lock:
            self.v = 2
            assert self.v == 2
            # start our thing that will be blocked, then sleep to make sure
            # it can't do its thing
            s = self.do_spawn(set_v1)
            sleep(0.2)
            assert self.v == 2

        # now wait for the other to complete, and check it could
        s.wait()
        assert self.v == 1
