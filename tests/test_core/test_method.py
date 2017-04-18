import unittest

# module imports
from malcolm.core.controller import Controller
from malcolm.core.process import Process
from malcolm.core.hook import Hook
from malcolm.core.part import Part
from malcolm.core.context import Context
from malcolm.core.methodmodel import OPTIONAL, REQUIRED, method_takes, \
    method_returns
from malcolm.modules.builtin.vmetas import StringMeta


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
        self.part = MyPart("test_part")
        self.controller = MyController(self.process, "mri", [self.part])
        self.process.add_controller("mri", self.controller)
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
        f = method_view.post_async('testAsync', 'y')
        assert f.result().ret == 'testAsyncy'

