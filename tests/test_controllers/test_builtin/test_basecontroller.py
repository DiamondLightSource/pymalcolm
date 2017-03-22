import unittest
from mock import Mock

from malcolm.core import Part, Process
from malcolm.controllers.builtin.basecontroller import BaseController


class MyPart(Part):
    @BaseController.Init
    def init(self, context, hup):
        self.context = context
        self.hup = hup

    @BaseController.Halt
    def halt(self, context):
        self.halted = True


class TestBaseControllerInit(unittest.TestCase):
    def test_init(self):
        params = Mock()
        params.mri = "MyMRI"
        process = Mock()
        o = BaseController(process, [], params)
        assert o.mri == params.mri
        assert o.params is params
        assert o.process is process


class TestBaseController(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.params = Mock()
        self.params.mri = "MyMRI"
        self.part = MyPart(self.process, "testpart")
        self.o = BaseController(self.process, [self.part], self.params)

    def start_process(self):
        self.process.add_controller(self.params.mri, self.o)
        self.process.start()
        self.addCleanup(self.stop_process)

    def stop_process(self):
        if self.process.started:
            self.process.stop()

    def test_process_init(self,):
        assert not hasattr(self.part, "context")
        self.start_process()
        assert self.part.hup == self.o.hup

    def test_process_stop(self):
        self.start_process()
        assert not hasattr(self.part, "halted")
        self.process.stop()
        assert self.part.halted is True

    def test_hup(self):
        self.o.hup = Mock(wraps=self.o.hup)
        self.start_process()
        self.part.hup()
        self.o.hup.assert_called_once()
