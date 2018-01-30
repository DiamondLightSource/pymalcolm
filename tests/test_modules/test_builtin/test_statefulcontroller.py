import unittest

from malcolm.compat import OrderedDict
from malcolm.core import Part, Process
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.builtin.hooks import ResetHook, DisableHook, InitHook, \
    HaltHook
from malcolm.modules.builtin.util import StatefulStates


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
    reset_done, disable_done, started, halted = False, False, False, False

    def on_hook(self, hook):
        if isinstance(hook, ResetHook):
            self.reset_done = True
        elif isinstance(hook, DisableHook):
            self.disable_done = True
        elif isinstance(hook, InitHook):
            self.started = True
        elif isinstance(hook, HaltHook):
            self.halted = True


class TestStatefulController(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.part = MyPart("testpart")
        self.o = StatefulController("MyMRI")
        self.o.add_part(self.part)
        self.process.add_controller(self.o)
        self.b = self.process.block_view("MyMRI")

    def start_process(self):
        self.process.start()
        self.addCleanup(self.stop_process)

    def stop_process(self):
        if self.process.started:
            self.process.stop(timeout=1)

    def test_process_init(self, ):
        assert not self.part.started
        self.start_process()
        assert self.part.started

    def test_process_stop(self):
        self.start_process()
        assert not self.part.halted
        self.process.stop(timeout=1)
        assert self.part.halted

    def test_init(self):
        assert self.b.state.value == "Disabled"
        self.start_process()
        assert list(self.b) == ['meta', 'health', 'state', 'disable', 'reset']
        assert self.b.state.value == "Ready"

    def test_reset_fails_from_ready(self):
        self.start_process()
        with self.assertRaises(TypeError):
            self.o.reset()
        assert not self.part.reset_done

    def test_disable(self):
        self.start_process()
        assert not self.part.disable_done
        self.b.disable()
        assert self.part.disable_done
        assert self.b.state.value == "Disabled"
        assert not self.part.reset_done
        self.b.reset()
        assert self.part.reset_done
        assert self.b.state.value == "Ready"





