import unittest

from malcolm.core import Part, Controller, Process
from malcolm.modules.pmac import parts


class TestBeamSelectorPart(unittest.TestCase):

    def setUp(self):
        self.controller = Controller("test_controller")
        self.process = Process("test_process")

    def test_init(self):
        assert self.controller, "Controller failed"
        assert self.process, "Process failed"
