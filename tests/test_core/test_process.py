import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths


import unittest
from mock import MagicMock

# module imports
from malcolm.core.process import Process
from malcolm.core.controller import Controller


class TestProcess(unittest.TestCase):

    def setUp(self):
        self.o = Process("proc")
        self.o.start()

    def tearDown(self):
        self.o.stop()

    def test_init(self):
        self.assertEqual(self.o.name, "proc")

    def test_add_controller(self):
        controller = MagicMock()
        self.o.add_controller("mri", controller)
        self.assertEqual(self.o.get_controller("mri"), controller)

    def test_init_controller(self):
        class InitController(Controller):
            init = False
            @Process.Init
            def do_init(self):
                self.init = True

        c = InitController(self.o, "mri", [])
        self.assertEqual(c.init, True)

    def test_publish_controller(self):
        class PublishController(Controller):
            published = []
            @Process.Publish
            def do_publish(self, published):
                self.published = published

        c = PublishController(self.o, "mri", [])
        self.assertEqual(c.published, ["mri"])
        self.o.add_controller("mri2", MagicMock())
        self.assertEqual(c.published, ["mri", "mri2"])
        self.o.add_controller("mri3", MagicMock(), False)
        self.assertEqual(c.published, ["mri", "mri2"])
        self.o.remove_controller("mri2")
        self.assertEqual(c.published, ["mri"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
