import unittest

from mock import MagicMock

from malcolm.core import Process, ProcessStartHook
from malcolm.core.controller import Controller
from malcolm.testutil import PublishController, UnpublishableController


class TestProcess(unittest.TestCase):
    def setUp(self):
        self.o = Process("proc")
        self.o.start()

    def tearDown(self):
        self.o.stop(timeout=1)

    def test_init(self):
        assert self.o.name == "proc"

    def test_add_controller(self):
        controller = MagicMock(mri="mri")
        self.o.add_controller(controller)
        assert self.o.get_controller("mri") == controller

    def test_init_controller(self):
        class InitController(Controller):
            init = False

            def on_hook(self, hook):
                if isinstance(hook, ProcessStartHook):
                    self.init = True

        c = InitController("mri")
        self.o.add_controller(c)
        assert c.init is True

    def test_publish_controller(self):
        c = PublishController("mri")
        self.o.add_controller(c)
        assert c.published == ["mri"]
        self.o.add_controller(Controller(mri="mri2"))
        assert c.published == ["mri", "mri2"]
        self.o.add_controller(UnpublishableController("mri3"))
        assert c.published == ["mri", "mri2"]
