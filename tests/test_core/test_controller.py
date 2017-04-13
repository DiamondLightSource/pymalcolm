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
from malcolm.core.controller import Controller
from malcolm.core.process import Process
from malcolm.core.hook import Hook
from malcolm.core.part import Part
from malcolm.core.alarm import Alarm, AlarmSeverity
from malcolm.core.context import Context
from malcolm.core.model import Model
from malcolm.core.blockmodel import BlockModel
from malcolm.core.queue import Queue
from malcolm.core.request import Post, Subscribe, Put, Get, Unsubscribe
from malcolm.core.response import Return, Update, Error
from malcolm.core.errors import UnexpectedError, AbortedError

from malcolm.vmetas.builtin import StringMeta
from malcolm.core.mapmeta import MapMeta
from malcolm.core.methodmodel import MethodModel, OPTIONAL, REQUIRED
from malcolm.core import method_takes, method_returns


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

    @method_takes()
    @method_returns('ret', StringMeta(), OPTIONAL)
    def my_method(self, returns=MapMeta()):
        returns.ret = 'world'
        return returns

    def create_attributes(self):
        meta = StringMeta(description="MyString")
        self.myAttribute = meta.create_attribute(initial_value='hello_block')
        yield "myAttribute", self.myAttribute, self.myAttribute.set_value


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.process = Process("proc")
        self.part = MyPart("test_part")
        self.part2 = MyPart("test_part2")
        self.o = MyController(self.process, "mri", [self.part, self.part2])
        self.context = Context("Context", self.process)
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_init(self):
        self.assertEqual(self.o.mri, "mri")
        self.assertEqual(self.o.process, self.process)

    def test_run_hook(self):
        context = MagicMock()
        context2 = MagicMock()
        part_contexts = {self.part: context, self.part2: context2}
        result = self.o.run_hook(self.o.TestHook, part_contexts)
        self.assertEquals(result,
                          dict(test_part=dict(foo="bar"),
                               test_part2=dict(foo="bar")))
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
        context2 = MagicMock()
        self.part.exception = MyException()
        part_contexts = {self.part: context, self.part2: context2}
        with self.assertRaises(Exception) as cm:
            self.o.run_hook(self.o.TestHook, part_contexts)
        self.assertIs(self.part.context, None)
        self.assertIs(cm.exception, self.part.exception)

    def test_run_hook_aborted(self):
        context = MagicMock()
        context2 = MagicMock()
        part_contexts = {self.part: context, self.part2: context2}
        with patch.object(Queue, 'get',
                          return_value=(self.part, AbortedError())):
            with self.assertRaises(AbortedError):
                self.o.run_hook(self.o.TestHook, part_contexts)

    def test_set_health(self):
        self.o.set_health(self.part,
                          Alarm(severity=AlarmSeverity.MINOR_ALARM))
        self.o.set_health(self.part2,
                          Alarm(severity=AlarmSeverity.MAJOR_ALARM))
        assert self.o.health.alarm.severity == AlarmSeverity.MAJOR_ALARM

        self.o.set_health(self.part,
                          Alarm(severity=AlarmSeverity.UNDEFINED_ALARM))
        self.o.set_health(self.part2,
                          Alarm(severity=AlarmSeverity.INVALID_ALARM))
        assert self.o.health.alarm.severity == AlarmSeverity.UNDEFINED_ALARM

        self.o.set_health(self.part)
        self.o.set_health(self.part2)
        assert self.o.health.value == "OK"

    def test_make_view(self):
        method_view = self.o._make_appropriate_view(self.context, self.part.my_method)
        attribute_view = self.o._make_appropriate_view(self.context, self.part.myAttribute)
        dict_view = self.o._make_appropriate_view(self.context,
                                                  {'a': self.part.myAttribute, 'm':self.part.my_method})
        list_view = self.o._make_appropriate_view(self.context,
                                                  [self.part.myAttribute, self.part.my_method])

        model = Model()
        model_view = self.o._make_appropriate_view(self.context, model)

        none_view = self.o._make_appropriate_view(self.context, None)

        block_data = BlockModel()
        block_data.set_endpoint_data("attr", StringMeta().create_attribute())
        block_data.set_endpoint_data("method", MethodModel())
        block_data.set_notifier_path(MagicMock(), ["block"])
        block_view = self.o._make_appropriate_view(self.context, block_data)

        # Todo check create_part_contexts worked
        self.o.create_part_contexts()

        # using __call__
        assert method_view().ret == 'world'
        assert attribute_view.value == "hello_block"
        assert dict_view['a'].value == "hello_block"
        assert list_view[0].value == "hello_block"

    def test_handle_request(self):
        q = Queue()

        request = Get(id=41, path=["mri", "myAttribute"],
                      callback=q.put)
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 41)
        self.assertEqual(response.value["value"], "hello_block")
        # It's part2 that will get the attribute as it was defined second
        self.part2.myAttribute.meta.writeable = False
        request = Put(id=42, path=["mri", "myAttribute"],
                      value='hello_block', callback=q.put)
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Error)  # not writeable
        self.assertEqual(response.id, 42)

        self.part2.myAttribute.meta.writeable = True
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 42)
        self.assertEqual(response.value, "hello_block")

        request = Post(id=43, path=["mri", "my_method"],
                      callback=q.put)
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 43)
        self.assertEqual(response.value['ret'], "world")

        # cover the controller._handle_post path for parameters
        request = Post(id=43, path=["mri", "my_method"],
                      parameters={'dummy': 1}, callback=q.put)
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 43)
        self.assertEqual(response.value['ret'], "world")

        request = Subscribe(id=44, path=["mri", "myAttribute"],
                            delta=False, callback=q.put)
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Update)
        self.assertEqual(response.id, 44)
        self.assertEqual(response.value["typeid"], "epics:nt/NTScalar:1.0")
        self.assertEqual(response.value["value"], "hello_block")

        request = Unsubscribe(id=44, callback=q.put)
        self.o.handle_request(request)
        response = q.get(timeout=.1)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 44)

if __name__ == "__main__":
    unittest.main(verbosity=2)
