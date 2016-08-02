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
from malcolm.core.response import Response, Error, Return, Update, Delta
from malcolm.core.request import Request
from malcolm.core.method import Method
from malcolm.core.future import Future, TimeoutError
from malcolm.core.meta import Meta
from malcolm.metas.scalarmeta import ScalarMeta
from malcolm.core.attribute import Attribute
from malcolm.core.block import Block
from malcolm.core.serializable import Serializable

#import logging
#logging.basicConfig(level=logging.DEBUG)

class TestWarning(Exception):
    pass

class TestTask(unittest.TestCase):

    def setUp(self):
        self.callback_result = 0
        self.callback_value = ''
        meta = ScalarMeta("meta for unit tests")
        self.block = MagicMock()
        self.proc = MagicMock(q=queue.Queue())
        self.proc.create_queue = MagicMock(side_effect=queue.Queue)
        self.attr = Attribute(meta)
        self.attr.set_parent(self.block, "testAttr")
        self.attr2 = Attribute(meta)
        self.attr2.set_parent(self.block, "testAttr2")
        self.method = Method("method for unit tests")
        self.method.set_parent(self.block, "testFunc")
        self.method2 = Method("method for unit tests")
        self.method2.set_parent(self.block, "testFunc")
        self.bad_called_back = False

    def test_init(self):
        t = Task("testTask", self.proc)
        self.assertIsInstance(t._logger, logging.Logger)
        self.assertIsInstance(t.q, queue.Queue)
        self.assertEqual(t.process, self.proc)

    def test_put_async(self):
        t = Task("testTask", self.proc)
        t.put_async(self.attr, "testValue")
        req = self.proc.q.get(timeout=0)
        self.assertIsInstance(req, Request)
        self.assertEqual(req.endpoint,
                         [self.block.name, 'testAttr', 'value'])
        self.assertEqual(len(t._futures), 1)

        d = {self.attr: "testValue", self.attr2: "testValue2"}
        t.put_async(d)
        self.proc.q.get(timeout=0)
        req2 = self.proc.q.get(timeout=0)
        self.assertEqual(self.proc.q.qsize(), 0)
        self.assertIsInstance(req2, Request)
        self.assertEqual(len(t._futures), 3)

    def test_put(self):
        # single attribute
        t = Task("testTask", self.proc)
        resp = Return(0, None, None)
        resp.set_value('testVal')
        # cheat and add the response before the blocking call to put
        t.q.put(resp)
        t.stop()
        t.put(self.attr, "testValue")
        self.assertEqual(len(t._futures), 0)
        self.assertEqual(self.proc.q.qsize(), 1)

    def test_post(self):
        t = Task("testTask", self.proc)
        resp1 = Return(0, None, None)
        resp1.set_value('testVal')
        resp2 = Error(1, None, None)
        # cheat and add the responses before the blocking call to put
        t.q.put(resp1)
        t.q.put(resp2)
        t.stop()
        t.post(self.method, "testParm")
        t.post(self.method, "testParm2")
        self.assertEqual(len(t._futures), 0)
        self.assertEqual(self.proc.q.qsize(), 2)

    def test_wait_all(self):
        t = Task("testTask", self.proc)
        f1 = Future(t)
        f2 = Future(t)
        f3 = Future(t)
        f0 = Future(t)
        t._futures = {0: f0, 1: f1, 2: f2, 3: f3}
        f_wait1 = [f2, f0]
        self.assertRaises(queue.Empty, t.wait_all, f_wait1, 0)

        resp0 = Return(0, None, None)
        resp0.set_value('testVal')
        resp2 = Error(2, None, None)
        t.q.put(resp0)
        t.q.put(resp2)
        t.wait_all( f_wait1, 0)
        self.assertEqual(t._futures, {1: f1, 3: f3})
        self.assertEqual(f0.done(), True)
        self.assertEqual(f1.done(), False)
        self.assertEqual(f2.done(), True)
        self.assertEqual(f3.done(), False)
        self.assertEqual(self.proc.q.qsize(), 0)

        resp3 = Delta(3, None, None)
        t.q.put(resp3)
        f_wait1 = [f3]
        self.assertRaises(ValueError, t.wait_all, f_wait1, 0.01)
        t.stop()
        self.assertRaises(RuntimeWarning, t.wait_all, f_wait1, 0.01)

        resp1 = Return(1, None, None)
        resp1.set_value('testVal')
        t.q.put(resp1)
        self.assertRaises(queue.Empty, t.wait_all, f_wait1, 0.01)
        self.assertEqual(t._futures, {})

        t._futures = {0: f0, 1: f1, 2: f2}
        t.q.put(resp1)
        t.q.put(Task.TASK_STOP)
        self.assertEqual(f1.result(), 'testVal')

    def test_wait_all_missing_futures(self):
        # unsolicited response
        t = Task("testTask", self.proc)
        f1 = Future(t)
        resp10 = Return(10, None, None)
        t.q.put(resp10)
        t.q.put(Task.TASK_STOP)
        self.assertRaises(RuntimeWarning, t.wait_all, f1, 0)

        # same future twice
        f2 = Future(t)
        t._futures = {1: f2}
        resp1 = Return(1, None, None)
        t.q.put(resp1)
        t.q.put(Task.TASK_STOP)
        t.wait_all(f2,0)
        t.wait_all(f2,0)


    def _callback(self, value, a, b):
        self.callback_result = a+b
        self.callback_value = value

    def test_subscribe(self):
        t = Task("testTask", self.proc)
        resp = Update(0, None, None)
        resp.set_value('changedVal')
        t.q.put(resp)
        t.stop()

        new_id = t.subscribe(self.attr, self._callback, 3, 5)
        f1 = Future(t)
        t._futures = {1: f1}

        self.assertRaises(RuntimeWarning, t.wait_all, f1, 0)
        self.assertEqual(self.callback_value, 'changedVal')
        self.assertEqual(self.callback_result, 8)
        t.unsubscribe(new_id)

    def test_callback_error(self):
        t = Task("testTask", self.proc)
        resp = Error(0, None, None)
        resp.set_message('error')
        t.q.put(resp)
        t.stop()

        t.subscribe(self.attr, self._callback, 3, 5)
        f1 = Future(t)
        t._futures = {1: f1}
        self.assertRaises(RuntimeError, t.wait_all, f1, 0)

    def test_callback_unexpected(self):
        t = Task("testTask", self.proc)
        resp = Delta(0, None, None)
        t.q.put(resp)
        t.stop()
        t.subscribe(self.attr, self._callback, 3, 5)
        f1 = Future(t)
        t._futures = {1: f1}
        self.assertRaises(ValueError, t.wait_all, f1, 0)


    def _bad_callback(self, value):
        self.bad_called_back = True
        raise TestWarning()

    def test_callback_crash(self):
        t = Task("testTask", self.proc)
        resp = Update(0, None, None)
        resp.set_value('changedVal')
        t.q.put(resp)
        t.stop()

        t.subscribe(self.attr, self._bad_callback)
        f1 = Future(t)
        t._futures = {1: f1}
        self.assertRaises(RuntimeWarning, t.wait_all, f1, 0)
        self.assertEquals(self.bad_called_back, True)

    def test_when_matches(self):
        t = Task("testTask", self.proc)
        f = t.when_matches(self.attr, "matchTest")

        # match (response goes to the subscription at id 1,
        # not the future at id 0)
        resp = Update(1, None, None)
        resp.set_value('matchTest')
        t.q.put(resp)
        t.stop()
        self.assertEqual(f[0].result(0),'matchTest')

    def test_not_when_matches(self):
        t = Task("testTask", self.proc)
        f = t.when_matches(self.attr, "matchTest")

        # match (response goes to the subscription at id 1,
        # not the future at id 0)
        resp = Update(1, None, None)
        resp.set_value('NOTmatchTest')
        t.q.put(resp)
        t.stop()

        # this will abort the task because f[0] never gets filled
        self.assertRaises(RuntimeWarning, f[0].result)
