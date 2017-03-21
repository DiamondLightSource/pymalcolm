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
from malcolm.core.queue import Queue
from malcolm.compat import queue, maybe_import_cothread

class TestQueue(unittest.TestCase):

    def check_put_get(self, q):
        q.put('hello')
        q.put('world')
        assert q.get(1) == 'hello'
        assert q.get(1) == 'world'




    def test_queue(self):
        q = Queue()
        self.check_put_get(q)

        # where we are using cothread - retest without it for coverage
        if q.cothread:
            with patch('malcolm.compat.maybe_import_cothread',
                              return_value=None):
                q2 = Queue()
                self.check_put_get(q2)




