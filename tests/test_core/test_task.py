import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, ANY
import time

#module imports
from malcolm.compat import queue
from malcolm.core.task import Task
from malcolm.core import AbortedError, ResponseError, UnexpectedError
from malcolm.core.spawnable import Spawnable
from malcolm.core.response import Error, Return, Update, Delta
from malcolm.core.request import Request
from malcolm.core.methodmeta import MethodMeta
from malcolm.core.future import Future
from malcolm.core.vmetas import StringMeta
from malcolm.core.elementmap import ElementMap
from malcolm.core import Process, Block, SyncFactory


#import logging
#logging.basicConfig(level=logging.DEBUG)

class TestWarning(Exception):
    pass

class TestTask(unittest.TestCase):

    def setUp(self):
        self.callback_result = 0
        self.callback_value = ''
        meta = StringMeta("meta for unit tests")
        self.proc = MagicMock(q=queue.Queue())
        self.proc.create_queue = MagicMock(side_effect=queue.Queue)
        self.block = Block()
        self.block.set_process_path(self.proc, ("testBlock",))
        self.attr = meta.make_attribute()
        self.attr2 = meta.make_attribute()
        self.method = MethodMeta("method for unit tests")
        self.method.returns.set_elements(ElementMap(dict(ret=StringMeta())))
        self.method2 = MethodMeta("method for unit tests")
        self.block.replace_endpoints(
            dict(testFunc=self.method, testFunc2=self.method2,
                 testAttr=self.attr, testAttr2=self.attr2))
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
                         ['testBlock', 'testAttr', 'value'])
        self.assertEqual(req.value, "testValue")
        self.assertEqual(len(t._futures), 1)

    def test_put_many_async(self):
        t = Task("testTask", self.proc)
        t.put_many_async(self.block, dict(
            testAttr="testValue", testAttr2="testValue2"))
        reqs = [self.proc.q.get(timeout=0), self.proc.q.get(timeout=0)]
        self.assertEqual(self.proc.q.qsize(), 0)
        self.assertEqual(len(t._futures), 2)
        values = list(sorted((req.endpoint, req.value) for req in reqs))
        self.assertEqual(values[0][0], ['testBlock', 'testAttr', 'value'])
        self.assertEqual(values[0][1], 'testValue')
        self.assertEqual(values[1][0], ['testBlock', 'testAttr2', 'value'])
        self.assertEqual(values[1][1], 'testValue2')

    def test_put(self):
        # single attribute
        t = Task("testTask", self.proc)
        resp = Return(1, None, None)
        resp.set_value('testVal')
        # cheat and add the response before the blocking call to put
        t.q.put(resp)
        t.stop()
        t.put(self.attr, "testValue")
        self.assertEqual(len(t._futures), 0)
        self.assertEqual(self.proc.q.qsize(), 1)

    def test_put_many(self):
        # many attributes
        t = Task("testTask", self.proc)
        resp1 = Return(1, None, None)
        resp1.set_value('testVal1')
        resp2 = Return(2, None, None)
        resp2.set_value('testVal2')
        # cheat and add the response before the blocking call to put
        t.q.put(resp1)
        t.q.put(resp2)
        t.stop()
        t.put_many(self.block, dict(
            testAttr="testValue", testAttr2="testValue2"))
        self.assertEqual(len(t._futures), 0)
        self.assertEqual(self.proc.q.qsize(), 2)

    def test_post(self):
        t = Task("testTask", self.proc)
        resp1 = Return(1, None, None)
        resp1.set_value(dict(ret='testVal'))
        resp2 = Error(2, None, "")
        # cheat and add the responses before the blocking call to put
        t.q.put(resp1)
        t.q.put(resp2)
        t.stop()
        t.post(self.method, {"a": "testParm"})
        self.assertRaises(ResponseError, t.post, self.method, {"a": "testParm2"})
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
        resp2 = Error(2, None, "")
        t.q.put(resp0)
        t.q.put(resp2)
        self.assertRaises(ResponseError, t.wait_all, f_wait1, 0)
        self.assertEqual(t._futures, {1: f1, 3: f3})
        self.assertEqual(f0.done(), True)
        self.assertEqual(f1.done(), False)
        self.assertEqual(f2.done(), True)
        self.assertEqual(f3.done(), False)
        self.assertEqual(self.proc.q.qsize(), 0)

        resp3 = Delta(3, None, None)
        t.q.put(resp3)
        f_wait1 = [f3]
        self.assertRaises(UnexpectedError, t.wait_all, f_wait1, 0.01)
        t.stop()
        self.assertRaises(AbortedError, t.wait_all, f_wait1, 0.01)

        resp1 = Return(1, None, None)
        resp1.set_value('testVal')
        t.q.put(resp1)
        self.assertRaises(queue.Empty, t.wait_all, f_wait1, 0.01)
        self.assertEqual(t._futures, {})

        t._futures = {0: f0, 1: f1, 2: f2}
        t.q.put(resp1)
        t.q.put(Spawnable.STOP)
        self.assertEqual(f1.result(), 'testVal')

    def test_wait_all_missing_futures(self):
        # unsolicited response
        t = Task("testTask", self.proc)
        f1 = Future(t)
        resp10 = Return(10, None, None)
        t.q.put(resp10)
        t.q.put(Spawnable.STOP)
        self.assertRaises(AbortedError, t.wait_all, f1, 0)

        # same future twice
        f2 = Future(t)
        t._futures = {1: f2}
        resp1 = Return(1, None, None)
        t.q.put(resp1)
        t.q.put(Spawnable.STOP)
        t.wait_all(f2,0)
        t.wait_all(f2,0)


    def _callback(self, value, a, b):
        self.callback_result = a+b
        self.callback_value = value

    def test_subscribe(self):
        t = Task("testTask", self.proc)
        resp = Update(1, None, None)
        resp.set_value('changedVal')
        t.q.put(resp)
        t.stop()

        new_id = t.subscribe(self.attr, self._callback, 3, 5)
        f1 = Future(t)
        t._futures = {1: f1}

        self.assertRaises(AbortedError, t.wait_all, f1, 0)
        self.assertEqual(self.callback_value, 'changedVal')
        self.assertEqual(self.callback_result, 8)
        t.unsubscribe(new_id)

    def test_callback_error(self):
        t = Task("testTask", self.proc)
        resp = Error(1, None, None)
        resp.set_message('error')
        t.q.put(resp)
        t.stop()

        t.subscribe(self.attr, self._callback, 3, 5)
        f1 = Future(t)
        t._futures = {1: f1}
        self.assertRaises(ResponseError, t.wait_all, f1, 0)

    def test_callback_unexpected(self):
        t = Task("testTask", self.proc)
        resp = Delta(1, None, None)
        t.q.put(resp)
        t.stop()
        t.subscribe(self.attr, self._callback, 3, 5)
        f1 = Future(t)
        t._futures = {1: f1}
        self.assertRaises(UnexpectedError, t.wait_all, f1, 0)

    def _bad_callback(self, value):
        self.bad_called_back = True
        raise TestWarning()

    def test_callback_crash(self):
        t = Task("testTask", self.proc)
        resp = Update(1, None, None)
        resp.set_value('changedVal')
        t.q.put(resp)
        t.stop()

        t.subscribe(self.attr, self._bad_callback)
        f1 = Future(t)
        t._futures = {1: f1}
        self.assertRaises(TestWarning, t.wait_all, f1, 0)
        self.assertEquals(self.bad_called_back, True)

    def test_sleep(self):
        t = Task("testTask", self.proc)
        start = time.time()
        t.sleep(0.05)
        end = time.time()
        self.assertAlmostEqual(end-start, 0.05, delta=0.005)

    def test_when_matches(self):
        t = Task("testTask", self.proc)

        f = t.when_matches_async(self.attr, "matchTest")
        resp = Update(1, None, None)
        resp.set_value('matchTest')
        t.q.put(resp)
        self.assertEqual(f[0].result(0), 'matchTest')
        t.stop()

    def test_not_when_matches(self):
        t = Task("testTask", self.proc)
        f = t.when_matches_async(self.attr, "matchTest")

        # match (response goes to the subscription at id 1,
        # not the future at id 0)
        resp = Update(1, None, None)
        resp.set_value('NOTmatchTest')
        t.q.put(resp)
        t.stop()

        # this will abort the task because f[0] never gets filled
        self.assertRaises(AbortedError, f[0].result)

    def test_start_default_raises(self):
        t = Task("t", self.proc)
        self.assertRaises(AssertionError, t.start)

    def test_clear_spawn_functions(self):
        t = Task("testTask", self.proc)
        f = MagicMock()
        t.define_spawn_function(None)
        self.assertEquals([(None, (), ANY)], t._spawn_functions)

    def test_clear_raises_if_running(self):
        proc = Process("proc", SyncFactory("sync"))
        t = Task("testTask", proc)
        import time
        def f():
            time.sleep(0.05)
        t.define_spawn_function(f)
        start = time.time()
        t.start()
        self.assertRaises(UnexpectedError, t.define_spawn_function, None)
        t.wait()
        end = time.time()
        self.assertAlmostEqual(end-start, 0.05, delta=0.03)
        t.define_spawn_function(None)
        del proc.sync_factory

if __name__ == "__main__":
    unittest.main(verbosity=2)
