import time
import unittest

import pytest
from mock import ANY, MagicMock

from malcolm.core import Process
from malcolm.core.context import Context
from malcolm.core.errors import AbortedError, BadValueError, ResponseError, TimeoutError
from malcolm.core.future import Future
from malcolm.core.request import Post, Put, Subscribe, Unsubscribe
from malcolm.core.response import Error, Return, Update


class MyWarning(Exception):
    pass


class TestContext(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.controller = MagicMock(mri="block")
        self.process.add_controller(self.controller)
        self.o = Context(self.process)

    def assert_handle_request_called_with(self, *requests):
        assert self.controller.handle_request.call_count == len(requests)
        for i, request in enumerate(requests):
            actual = self.controller.handle_request.call_args_list[i][0][0]
            assert request.to_dict() == actual.to_dict()

    def test_aborts_timeout_zero(self):
        self.o.ignore_stops_before_now()
        self.o.sleep(0)
        self.o.ignore_stops_before_now()
        self.o.ignore_stops_before_now()
        self.o.stop()
        with self.assertRaises(AbortedError) as cm:
            self.o.sleep(0)
        assert str(cm.exception) == "Aborted waiting for []"

    def test_block_view(self):
        self.o.block_view("block")
        self.controller.block_view.assert_called_once_with(ANY)

    def test_put(self):
        self.o._q.put(Return(1, 33))
        ret = self.o.put(["block", "attr", "value"], 32)
        self.assert_handle_request_called_with(Put(1, ["block", "attr", "value"], 32))
        assert ret == 33

    def test_put_failure(self):
        self.o._q.put(Error(1, ResponseError("Test Exception")))
        with self.assertRaises(ResponseError) as cm:
            self.o.put(["block", "attr", "value"], 32)
        assert str(cm.exception) == "Test Exception"

    def test_post(self):
        self.o._q.put(Return(1, dict(a=2)))
        result = self.o.post(["block", "method"], dict(b=32))
        self.assert_handle_request_called_with(Post(1, ["block", "method"], dict(b=32)))
        assert result == dict(a=2)

    def test_post_failure(self):
        self.o._q.put(Error(1, ValueError("Test Exception")))
        with self.assertRaises(ValueError) as cm:
            self.o.post(["block", "method"], dict(b=32))
        assert str(cm.exception) == "Test Exception"

    def test_subscribe(self):
        cb = MagicMock()
        f = self.o.subscribe(["block", "attr", "value"], cb, self.o, "arg2")
        self.assert_handle_request_called_with(Subscribe(1, ["block", "attr", "value"]))
        self.o._q.put(Update(1, "value1"))
        with self.assertRaises(TimeoutError):
            self.o.wait_all_futures(f, 0.01)
        cb.assert_called_once_with("value1", ANY, "arg2")
        # since args = self.o it should be a weak proxy in second argument
        cb.call_args[0][1]
        # TODO: giles cant work out how to check weakproxy equivalence??
        # self.assertEquals(param1, self.o)
        cb.reset_mock()
        self.o._q.put(Update(1, "value2"))
        self.o._q.put(Return(1))
        self.o.wait_all_futures(f, 0.01)
        cb.assert_called_once_with("value2", ANY, "arg2")
        assert f.result(0.01) is None

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

    @pytest.mark.timeout(1)
    def test_subscription_with_callback_calling_unsubscribe(self):
        # This test was designed to trigger a bug. Concluding a future inside a
        # callback, as is done here by unsubscribe() followed by sleep(0), would
        # not be recognised by the call to wait_all_futures(...). This would
        # result in an indefinite hang.

        def cb(value):
            self.o.unsubscribe_all()
            self.o._q.put(Return(1))  # Return from subscribe
            self.o.sleep(0)  # Service futures

        self.o.subscribe(["block", "attr", "value"], cb)  # id=1
        self.o._q.put(Update(1, "original_value"))  # Update from initial value

        future = self.o.put_async(["block", "attr2", "value"], "new")  # id=2
        self.o._q.put(Return(2))  # Return from put to attr2

        self.o.wait_all_futures(future)

    def test_many_puts(self):
        fs = [
            self.o.put_async(["block", "attr", "value"], 32),
            self.o.put_async(["block", "attr2", "value"], 32),
        ]
        with self.assertRaises(TimeoutError) as cm:
            self.o.wait_all_futures(fs, 0.01)
        assert str(cm.exception) == (
            "Timeout waiting for [block.attr.value.put_value(32), "
            "block.attr2.value.put_value(32)]"
        )
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
        self.assertAlmostEqual(end - start, 0.05, delta=0.01)

    def test_when_matches(self):
        self.o._q.put(Update(1, "value1"))
        self.o._q.put(Return(1))
        self.o.when_matches(["block", "attr", "value"], "value1", timeout=0.01)
        self.assert_handle_request_called_with(
            Subscribe(1, ["block", "attr", "value"]), Unsubscribe(1)
        )

    def test_when_matches_func(self):
        self.o._q.put(Update(1, "value1"))
        self.o._q.put(Return(1))

        def f(value):
            return value.startswith("v")

        self.o.when_matches(["block", "attr", "value"], f, timeout=0.01)
        self.assert_handle_request_called_with(
            Subscribe(1, ["block", "attr", "value"]), Unsubscribe(1)
        )

    def test_when_not_matches(self):
        self.o._q.put(Update(1, "value2"))
        with self.assertRaises(BadValueError) as cm:
            self.o.when_matches(
                ["block", "attr", "value"], "value1", ["value2"], timeout=0.01
            )
        assert str(cm.exception) == "Waiting for 'value1', got 'value2'"

        self.assert_handle_request_called_with(
            Subscribe(1, ["block", "attr", "value"]), Unsubscribe(1)
        )

    def test_ignore_stops_before_now(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32)]
        self.o.stop()
        self.o.ignore_stops_before_now()

        with self.assertRaises(TimeoutError):
            self.o.wait_all_futures(fs, 0)

        assert 0 == len(self.o._q._event_queue)

    def test_futures_exception(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32)]

        fs[0]._exception = BadValueError()
        fs[0]._state = Future.FINISHED
        with self.assertRaises(BadValueError) as cm:
            self.o.wait_all_futures(fs, 0)
        assert cm.exception is fs[0]._exception

    def test_futures_remaining_paths(self):
        fs = [self.o.put_async(["block", "attr", "value"], 32)]
        self.o.stop()
        with self.assertRaises(AbortedError) as cm:
            self.o.wait_all_futures(fs, 0)
        assert (
            str(cm.exception) == "Aborted waiting for [block.attr.value.put_value(32)]"
        )

    def test_timeout_bad(self):
        future = self.o.put_async(["block", "attr", "value"], 32)
        with self.assertRaises(TimeoutError) as cm:
            self.o.wait_all_futures(future, timeout=0.01)
        assert (
            str(cm.exception) == "Timeout waiting for [block.attr.value.put_value(32)]"
        )

    def test_timeout_good(self):
        future = self.o.put_async(["block", "attr", "value"], 32)
        self.o._q.put(Return(1))
        self.o.wait_all_futures(future, timeout=0.01)

    def test_event_timeout_bad(self):
        future = self.o.put_async(["block", "attr", "value"], 32)
        with self.assertRaises(TimeoutError) as cm:
            self.o.wait_all_futures(future, event_timeout=0.01)
        assert (
            str(cm.exception) == "Timeout waiting for [block.attr.value.put_value(32)]"
        )

    def test_event_timeout_good(self):
        future = self.o.put_async(["block", "attr", "value"], 32)
        self.o._q.put(Return(1))
        self.o.wait_all_futures(future, event_timeout=0.01)
