import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.spawned import Spawned
from malcolm.core.queue import Queue
from malcolm.core.errors import UnexpectedError
from multiprocessing.pool import ThreadPool


class TestSpawned(unittest.TestCase):

    @classmethod
    def do_div(cls, a, b, q, throw_me=None):
        if throw_me:
            q.put(throw_me)
            raise throw_me
        q.put(a/b)

    def setUp(self):
        pass

    def do_all(self, use_cothread, pool=None):
        q = Queue()
        s1 = Spawned(self.do_div, [40, 2, q, None],
                     {}, use_cothread, pool)
        assert s1.ready() is False
        s1.wait(1)
        assert s1.ready() is True
        assert q.get(1) == 20

        s2 = Spawned(self.do_div, [40, 2, q, UnexpectedError],
                     {}, use_cothread, pool)
        s2.wait(1)
        assert q.get(1) == UnexpectedError

    def test_all(self):
        self.do_all(True)
        pool = ThreadPool()
        self.do_all(False, pool)
        pool.close()
