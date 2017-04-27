import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
import thread

from malcolm.core.spawned import Spawned
from malcolm.core.queue import Queue
from malcolm.core.errors import UnexpectedError
from multiprocessing.pool import ThreadPool


def do_div(a, b, q, throw_me=None):
    if throw_me:
        q.put(throw_me)
        raise throw_me
    q.put(a / b)
    return a / b


class TestSpawned(unittest.TestCase):

    def setUp(self):
        self.pool = ThreadPool(4)
        self.q = Queue()

    def tearDown(self):
        self.pool.close()
        self.pool.join()

    def do_spawn(self, use_cothread, throw_me=None):
        s = Spawned(
            do_div, (40, 2, self.q, throw_me), {}, use_cothread, self.pool)
        return s

    def do_spawn_div(self, use_cothread):
        s = self.do_spawn(use_cothread)
        assert s.ready() is False
        s.wait(1)
        assert s.ready() is True
        assert self.q.get(1) == 20
        assert s.get() == 20

    def do_spawn_err(self, use_cothread):
        s = self.do_spawn(use_cothread, UnexpectedError)
        assert s.ready() is False
        s.wait(1)
        assert s.ready() is True
        assert self.q.get(1) == UnexpectedError
        self.assertRaises(UnexpectedError, s.get)

    def test_use_cothread(self):
        self.do_spawn_div(True)

    def test_not_use_cothread(self):
        self.do_spawn_div(False)

    def test_use_cothread_err(self):
        self.do_spawn_err(True)

    def test_not_use_cothread_err(self):
        self.do_spawn_err(False)
