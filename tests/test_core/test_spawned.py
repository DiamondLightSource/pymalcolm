import unittest

from malcolm.core import Queue, Spawned
from malcolm.core.errors import UnexpectedError


def do_div(a, b, q, throw_me=None):
    if throw_me:
        q.put(throw_me)
        raise throw_me
    q.put(a / b)
    return a / b


class TestSpawned(unittest.TestCase):
    def setUp(self):
        self.q = Queue()

    def do_spawn(self, throw_me=None):
        s = Spawned(do_div, (40, 2, self.q, throw_me), {})
        return s

    def test_spawn_div(self):
        s = self.do_spawn()
        assert s.ready() is False
        s.wait(1)
        assert s.ready() is True
        assert self.q.get(1) == 20
        assert s.get() == 20

    def test_spawn_err(self):
        s = self.do_spawn(UnexpectedError)
        assert s.ready() is False
        s.wait(1)
        assert s.ready() is True
        assert self.q.get(1) == UnexpectedError
        with self.assertRaises(UnexpectedError):
            s.get()
