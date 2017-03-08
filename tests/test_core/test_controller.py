import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
import gc
from mock import MagicMock, call, ANY

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.controller import Controller
from malcolm.core.process import Process
from malcolm.core.hook import Hook
from malcolm.core.part import Part


class MyController(Controller):
    TestHook = Hook()


class MyPart(Part):
    context = None
    exception = None

    @MyController.TestHook
    def func(self, context):
        if self.exception:
            raise self.exception
        self.context = context
        return dict(foo="bar")


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = Process("proc")
        self.part = MyPart(self.process, "test_part")
        self.o = MyController(self.process, "mri", [self.part])
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_init(self):
        self.assertEqual(self.o.mri, "mri")
        self.assertEqual(self.o.process, self.process)

    def test_run_hook(self):
        context = MagicMock()
        part_contexts = {self.part: context}
        result = self.o.run_hook(self.o.TestHook, part_contexts)
        self.assertEquals(result, dict(test_part=dict(foo="bar")))
        self.assertIs(self.part.context.anything, context.anything)
        del context
        del part_contexts
        gc.collect()
        with self.assertRaises(ReferenceError):
            self.part.context.anything

    def test_run_hook_raises(self):
        class MyException(Exception):
            pass
        context = MagicMock()
        self.part.exception = MyException()
        part_contexts = {self.part: context}
        with self.assertRaises(Exception) as cm:
            self.o.run_hook(self.o.TestHook, part_contexts)
        self.assertIs(self.part.context, None)
        self.assertIs(cm.exception, self.part.exception)

if __name__ == "__main__":
    unittest.main(verbosity=2)
