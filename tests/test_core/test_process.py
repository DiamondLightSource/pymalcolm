import unittest
from mock import MagicMock

from malcolm.core.process import Process
from malcolm.core.controller import Controller


class TestProcess(unittest.TestCase):

    def setUp(self):
        self.o = Process("proc")
        self.o.start()

    def tearDown(self):
        self.o.stop(timeout=1)

    def test_init(self):
        assert self.o.name == "proc"

    def test_add_controller(self):
        controller = MagicMock()
        self.o.add_controller("mri", controller)
        assert self.o.get_controller("mri") == controller

    def test_init_controller(self):
        class InitController(Controller):
            init = False
            @Process.Init
            def do_init(self):
                self.init = True

        c = InitController(self.o, "mri", [])
        self.o.add_controller("mri", c)
        assert c.init == True

    def test_publish_controller(self):
        class PublishController(Controller):
            published = []
            @Process.Publish
            def do_publish(self, published):
                self.published = published

        c = PublishController(self.o, "mri", [])
        self.o.add_controller("mri", c)
        assert c.published == ["mri"]
        self.o.add_controller("mri2", MagicMock())
        assert c.published == ["mri", "mri2"]
        self.o.add_controller("mri3", MagicMock(), False)
        assert c.published == ["mri", "mri2"]
        self.o.remove_controller("mri2")
        assert c.published == ["mri"]
