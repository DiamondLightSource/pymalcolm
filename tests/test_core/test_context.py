import unittest
from mock import MagicMock, ANY, call
import time

from malcolm.core.context import Context
from malcolm.core.errors import ResponseError, TimeoutError, BadValueError, \
    AbortedError
from malcolm.core.request import Put, Post, Subscribe, Unsubscribe
from malcolm.core.response import Error, Return, Update
from malcolm.core.process import Process
from malcolm.core.future import Future
from malcolm.compat import maybe_import_cothread


class MyWarning(Exception):
    pass


class TestContext(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.controller = MagicMock()
        self.process.add_controller("block", self.controller)
        self.o = Context(self.process)
        self.cothread = maybe_import_cothread()

    def test_aborts_timeout_zero(self):
        self.o.ignore_stops_before_now()
        self.o.sleep(0)
        self.o.ignore_stops_before_now()
        self.o.ignore_stops_before_now()
        self.o.stop()
        with self.assertRaises(AbortedError):
            self.o.sleep(0)

    def test_block_view(self):
        self.o.block_view("block")
        self.controller.make_view.assert_called_once_with(ANY)

    def test_put(self):
        self.o._q.put(Return(1, None))
        self.o.put(["block", "attr", "value"], 32)
        self.controller.handle_request.assert_called_once_with(
            Put(1, ["block", "attr", "value"], 32))

    def test_put_failure(self):
        self.o._q.put(Error(1, "Test Exception"))
        with self.assertRaises(ResponseError) as cm:
            self.o.put(["block", "attr", "value"], 32)
        assert str(cm.exception) == "Test Exception"

    def test_post(self):
        self.controller.validate_result.return_value = 22
        self.o._q.put(Return(1, dict(a=2)))
        result = self.o.post(["block", "method"], dict(b=32))
        self.controller.handle_request.assert_called_once_with(
            Post(1, ["block", "method"], dict(b=32)))
        self.controller.validate_result.assert_called_once_with(
            "method", dict(a=2))
        assert result == 22

    def test_post_failure(self):
        self.o._q.put(Error(1, "Test Exception"))
        with self.assertRaises(ResponseError) as cm:
            self.o.post(["block", "method"], dict(b=32))
        assert str(cm.exception) == "Test Exception"

    def test_subscribe(self):
        cb = MagicMock()
        f = self.o.subscribe(["block", "attr", "value"], cb, self.o, 'arg2')
        self.controller.handle_request.assert_called_once_with(
            Subscribe(1, ["block", "attr", "value"]))
        self.o._q.put(Update(1, "value1"))
        with self.assertRaises(TimeoutError):
            self.o.wait_all_futures(f, 0.01)
        cb.assert_called_once_with("value1", ANY, 'arg2')
        # since args = self.o it should be a weak proxy in second argument
        param1 = cb.call_args[0][1]
        # TODO: giles cant work out how to check weakproxy equivalence??
        # self.assertEquals(param1, self.o)
        cb.reset_mock()
        self.o._q.put(Update(1, "value2"))
        self.o._q.put(Return(1))
        self.o.wait_all_futures(f, 0.01)
        cb.assert_called_once_with("value2", ANY, 'arg2')
        assert f.result(0.01) == None

    def test_subscribe_cb_failure(self):
        def cb(value):
            raise MyWarning()

        f = self.o.subscribe(["block", "attr", "value"], cb)
        self.o._q.put(Update(1, "value1"))
        with self.assertRaises(MyWarning):
            self.o.wait_all_futures(f, 0.01)
        assert not f.done()
        self.o._q.put(Update(1, "value1"))
        with self.assertRaises(MyWarning):
            self.o.wait_all_futures(f, 0.01)
        assert not f.done()
        self.o._q.put(Return(1))
        self.o.wait_all_futures(f, 0.01)
        assert f.done()

    def test_many_puts(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32),
              self.o.put_async(["block", "attr2", "value"], 32)]
        with self.assertRaises(TimeoutError):
            self.o.wait_all_futures(fs, 0.01)
        assert [f.done() for f in fs] == [False, False]
        self.o._q.put(Return(2, None))
        assert [f.done() for f in fs] == [False, False]
        with self.assertRaises(TimeoutError):
            self.o.wait_all_futures(fs, 0.01)
        assert [f.done() for f in fs] == [False, True]
        self.o._q.put(Return(1, None))
        self.o.wait_all_futures(fs, 0.01)
        assert [f.done() for f in fs] == [True, True]
        self.o.wait_all_futures(fs, 0.01)
        assert [f.done() for f in fs] == [True, True]

    def test_sleep(self):
        start = time.time()
        self.o.sleep(0.05)
        end = time.time()
        self.assertAlmostEqual(end-start, 0.05, delta=0.01)

    def test_when_matches(self):
        self.o._q.put(Update(1, "value1"))
        self.o._q.put(Return(1))
        self.o.when_matches(["block", "attr", "value"], "value1", timeout=0.01)
        assert self.controller.handle_request.call_args_list == [
            call(Subscribe(1, ["block", "attr", "value"])),
            call(Unsubscribe(1))]

    def test_when_matches_func(self):
        self.o._q.put(Update(1, "value1"))
        self.o._q.put(Return(1))

        def f(value):
            return value.startswith("v")

        self.o.when_matches(["block", "attr", "value"], f, timeout=0.01)
        assert self.controller.handle_request.call_args_list == [
            call(Subscribe(1, ["block", "attr", "value"])),
            call(Unsubscribe(1))]

    def test_when_not_matches(self):
        self.o._q.put(Update(1, "value2"))
        with self.assertRaises(BadValueError):
            self.o.when_matches(
                ["block", "attr", "value"], "value1", ["value2"], timeout=0.01)
        assert self.controller.handle_request.call_args_list == [
            call(Subscribe(1, ["block", "attr", "value"])),
            call(Unsubscribe(1))]

    def test_ignore_stops_before_now(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32)]
        self.o.stop()
        self.o.ignore_stops_before_now()

        with self.assertRaises(TimeoutError):
            self.o.wait_all_futures(fs, 0)

        if self.cothread:
            assert 0 == len(self.o._q._event_queue)
        else:
            assert 0 == self.o._q._queue.qsize()

    def test_futures_exception(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32)]

        fs[0]._exception = BadValueError
        fs[0]._state = Future.FINISHED
        with self.assertRaises(BadValueError):
            self.o.wait_all_futures(fs, 0)

    def test_futures_remaining_paths(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32)]
        self.o.stop()
        with self.assertRaises(AbortedError):
            self.o.wait_all_futures(fs, 0)
