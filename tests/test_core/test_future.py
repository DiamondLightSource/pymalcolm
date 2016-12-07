import os
import sys
import logging

from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call, ANY

#module imports
from malcolm.compat import queue
from malcolm.core.task import Task
from malcolm.core.future import Future
from malcolm.core import ResponseError
from malcolm.core.response import Return, Error

#import logging
#logging.basicConfig(level=logging.DEBUG)

class TestFuture(unittest.TestCase):

    def setUp(self):
        self.proc = MagicMock(q=queue.Queue())
        self.proc.create_queue = MagicMock(return_value=queue.Queue())
        self.task = Task("testTask", self.proc)

    def test_set_result(self):
        f = Future(self.task)
        f.set_result("testResult")
        self.assertTrue(f.done())
        self.assertEqual(f.result(0), "testResult")

    def test_set_exception(self):
        f = Future(self.task)
        e = ValueError("test Error")
        f.set_exception(e)
        self.assertTrue(f.done())
        self.assertRaises(ValueError, f.result, 0)
        self.assertEqual(f.exception(), e)

    def test_result(self):
        # timeout due to no response arriving
        f0 = Future(self.task)
        f1 = Future(self.task)
        self.task._futures = {0: f0, 1: f1}
        self.assertRaises(queue.Empty, f0.result, 0)
        # return after waiting for response object
        resp0 = Return(0, None, None)
        resp0.set_value('testVal')
        resp1 = Error(1, None, "test Error")
        resp1.set_message('test Error')
        self.task.q.put(resp0)
        self.task.q.put(resp1)
        self.assertEqual(f0.result(),'testVal')

    def test_exception(self):
        # timeout due to no response arriving
        f0 = Future(self.task)
        f1 = Future(self.task)
        self.task._futures = {0: f0, 1: f1}
        self.assertRaises(queue.Empty, f0.exception, 0)
        # return after waiting for response object
        resp0 = Return(0, None, None)
        resp0.set_value('testVal')
        resp1 = Error(1, None, None)
        resp1.set_message('test Error')
        self.task.q.put(resp0)
        self.task.q.put(resp1)
        with self.assertRaises(ResponseError) as cm:
            f1.exception()
        self.assertEqual(str(cm.exception), 'test Error')
