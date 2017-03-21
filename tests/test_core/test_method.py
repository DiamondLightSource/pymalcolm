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
from malcolm.core.context import Context

from malcolm.vmetas.builtin import StringMeta
from malcolm.core.mapmeta import MapMeta
from malcolm.core.methodmodel import MethodModel, OPTIONAL, REQUIRED
from malcolm.core import method_takes, method_returns

class MyController(Controller):
    TestHook = Hook()


class MyPart(Part):
    context = None
    exception = None

    @method_takes('param1', StringMeta(), REQUIRED,
                  'param2', StringMeta(), REQUIRED)
    @method_returns('ret', StringMeta(), OPTIONAL)
    def my_method(self, params, returns):
        returns.ret = params.param1 + params.param2
        return returns

class TestMethod(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.part = MyPart(self.process, "test_part")
        self.controller = MyController(self.process, "mri", [self.part])
        self.context = Context("Context", self.process)
        self.block = self.controller.make_view(self.context)
        self.process.start()
        self.process.my_method_executed = False

    def tearDown(self):
        self.process.stop()

    def test_post(self):
        method_view = self.block.my_method
        result = method_view.post(param1='testPost', param2='y')
        assert result.ret == 'testPosty'

    def test_post_async(self):
        method_view = self.block.my_method
        f = method_view.post_async('testAsync','y')
        assert f.result().ret == 'testAsyncy'

