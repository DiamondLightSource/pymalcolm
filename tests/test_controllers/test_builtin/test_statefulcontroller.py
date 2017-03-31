import unittest
import pytest
from mock import Mock

from malcolm.compat import OrderedDict
from malcolm.core import Part, Process
from malcolm.controllers.builtin.statefulcontroller import StatefulController, \
    StatefulStates


class TestStates(unittest.TestCase):

    def setUp(self):
        self.o = StatefulStates()

    def test_init(self):
        expected = OrderedDict()
        expected['Resetting'] = {'Ready', 'Fault', 'Disabling'}
        expected['Ready'] = {"Fault", "Disabling"}
        expected['Fault'] = {"Resetting", "Disabling"}
        expected['Disabling'] = {"Disabled", "Fault"}
        expected['Disabled'] = {"Resetting"}
        assert self.o._allowed == expected

    def test_transition_allowed(self):
        assert self.o.transition_allowed("Ready", "Resetting") is False
        assert self.o.transition_allowed("Ready", "Disabling")

    def test_set_allowed(self):
        assert self.o.transition_allowed("Ready", "Resetting") is False
        self.o.set_allowed("Ready", "Resetting")
        assert self.o.transition_allowed("Ready", "Resetting")


class MyPart(Part):
    @StatefulController.Reset
    def reset(self, context):
        self.reset_done = True

    @StatefulController.Disable
    def disable(self, context):
        self.disable_done = True


class TestStatefulController(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.params = Mock()
        self.params.mri = "MyMRI"
        self.part = MyPart("testpart")
        self.o = StatefulController(self.process, [self.part], self.params)
        self.process.add_controller(self.params.mri, self.o)

    def start_process(self):
        self.process.start()
        self.addCleanup(self.process.stop)

    def test_init(self):
        assert self.o.state.value == "Disabled"
        self.start_process()
        assert self.o.state.value == "Ready"

    def test_reset_fails_from_ready(self):
        self.start_process()
        with pytest.raises(TypeError):
            self.o.reset()
        assert not hasattr(self.part, "reset_done")

    def test_disable(self):
        self.start_process()
        assert not hasattr(self.part, "disable_done")
        self.o.disable()
        assert self.part.disable_done
        assert self.o.state.value == "Disabled"
        assert not hasattr(self.part, "reset_done")
        self.o.reset()
        assert self.part.reset_done
        assert self.o.state.value == "Ready"





