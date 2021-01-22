import unittest

from mock import MagicMock

from malcolm.core.future import Future


class MyError(Exception):
    pass


class TestFuture(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()

    def test_set_result(self):
        f = Future(self.context)
        f.set_result("testResult")
        assert f.done()
        assert f.result(0) == "testResult"

    def test_set_exception(self):
        f = Future(self.context)
        e = ValueError("test Error")
        f.set_exception(e)
        assert f.done()
        with self.assertRaises(ValueError):
            f.result(timeout=0)
        assert f.exception() == e

    def test_result(self):
        f = Future(self.context)

        def wait_all_futures(fs, timeout):
            fs[0].set_result(32)

        self.context.wait_all_futures.side_effect = wait_all_futures

        assert f.result() == 32
        self.context.wait_all_futures.assert_called_once_with([f], None)
        self.context.wait_all_futures.reset_mock()
        assert f.result() == 32
        self.context.wait_all_futures.assert_not_called()

    def test_exception(self):
        f = Future(self.context)

        def wait_all_futures(fs, timeout):
            fs[0].set_exception(MyError())

        self.context.wait_all_futures.side_effect = wait_all_futures

        with self.assertRaises(MyError):
            f.result()

        self.context.wait_all_futures.assert_called_once_with([f], None)
        self.context.wait_all_futures.reset_mock()
        self.assertIsInstance(f.exception(), MyError)
        self.context.wait_all_futures.assert_not_called()
