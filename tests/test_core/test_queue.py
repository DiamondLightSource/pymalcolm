import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
import gc
from mock import MagicMock, call, ANY, patch

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
import threading
from malcolm.core.queue import Queue
from malcolm.core.errors import TimeoutError
from cothread import Spawn


class TestQueue(unittest.TestCase):

    def check_put_get(self, q, result_q=None):
        try:
            q.put('hello_block')
            q.put('world')
            assert q.get(1) == 'hello_block'
            assert q.get(1) == 'world'
            with self.assertRaises(TimeoutError):
                q.get(0)
        except Exception as e:
            if result_q:
                result_q.put(e)
            else:
                raise

    @classmethod
    def check_spawned_get(cls, q):
        q.get()

    def test_queue(self):
        results = Queue()
        q = Queue()
        self.check_put_get(q)

        if q.cothread:
            # re-stest in a separate cothread
            Spawn(self.check_put_get, q, results)
            if len(results._event_queue) > 0:
                res = results.get(0)
                raise res

            # retest without cothread for coverage
            #q2 = Queue(use_cothread=False)
            #self.check_put_get(q2)

            # Todo giles - not understood why this fails - coverage incomplete
            # retest in separate real thread
            # results2 = Queue(use_cothread=False)
            # t = threading.Thread(target=self.check_put_get,
            #                       args=(q, results2))
            # t.start()
            # t.join()
            # if not results2._queue.empty():
            #     res = results2.get(0)
            #     raise res
