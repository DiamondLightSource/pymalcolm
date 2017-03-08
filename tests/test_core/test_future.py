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
from malcolm.core.context import Context
from malcolm.core.future import Future
from malcolm.core.errors import ResponseError, TimeoutError
from malcolm.core.process import Process
from malcolm.core.response import Return, Error

#import logging
#logging.basicConfig(level=logging.DEBUG)

class TestError(Exception):
    pass


class TestFuture(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()

    def test_set_result(self):
        f = Future(self.context)
        f.set_result("testResult")
        self.assertTrue(f.done())
        self.assertEqual(f.result(0), "testResult")

    def test_set_exception(self):
        f = Future(self.context)
        e = ValueError("test Error")
        f.set_exception(e)
        self.assertTrue(f.done())
        self.assertRaises(ValueError, f.result, 0)
        self.assertEqual(f.exception(), e)

    def test_result(self):
        f = Future(self.context)

        def wait_all_futures(fs, timeout):
            fs[0].set_result(32)

        self.context.wait_all_futures.side_effect = wait_all_futures

        self.assertEqual(f.result(), 32)
        self.context.wait_all_futures.assert_called_once_with([f], None)
        self.context.wait_all_futures.reset_mock()
        self.assertEqual(f.result(), 32)
        self.context.wait_all_futures.assert_not_called()

    def test_exception(self):
        f = Future(self.context)

        def wait_all_futures(fs, timeout):
            fs[0].set_exception(TestError())

        self.context.wait_all_futures.side_effect = wait_all_futures

        with self.assertRaises(TestError):
            f.result()

        self.context.wait_all_futures.assert_called_once_with([f], None)
        self.context.wait_all_futures.reset_mock()
        self.assertIsInstance(f.exception(), TestError)
        self.context.wait_all_futures.assert_not_called()
