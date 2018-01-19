import unittest
import time

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Process, Part, call_with_params, \
    Context, ResponseError, AlarmStatus, AlarmSeverity, method_takes, \
    method_also_takes, REQUIRED
from malcolm.modules.scanning.parts import RunnableChildPart
from malcolm.modules.demo.blocks import ticker_block
from malcolm.compat import OrderedDict
from malcolm.modules.scanning.controllers import \
    RunnableController
from malcolm.modules.scanning.util import RunnableStates
from malcolm.core.vmetas import StringMeta


class TestRunnableStates(unittest.TestCase):

    def setUp(self):
        self.o = RunnableStates()

    def test_init(self):
        expected = OrderedDict()
        expected['Resetting'] = {"Ready", "Fault", "Disabling"}
        expected['Ready'] = {"Configuring", "Aborting", 'Saving', "Fault",
                             "Disabling", "Loading"}
        expected['Saving'] = {'Fault', 'Ready', 'Disabling'}
        expected['Loading'] = {'Disabling', 'Fault', 'Ready'}
        expected['Configuring'] = {"Armed", "Aborting", "Fault", "Disabling"}
        expected['Armed'] = {"Seeking", "Aborting", "Running",
                             "Fault", "Disabling", "Resetting"}
        expected['Running'] = {"PostRun", "Seeking", "Aborting", "Fault",
                               "Disabling"}
        expected['PostRun'] = {"Ready", "Armed", "Aborting", "Fault",
                               "Disabling"}
        expected['Seeking'] = {"Armed", "Paused", "Aborting", "Fault",
                               "Disabling"}
        expected['Paused'] = {"Seeking", "Running", "Aborting", "Fault",
                              "Disabling"}
        expected['Aborting'] = {"Aborted", "Fault", "Disabling"}
        expected['Aborted'] = {"Resetting", "Fault", "Disabling"}
        expected['Fault'] = {"Resetting", "Disabling"}
        expected['Disabling'] = {"Disabled", "Fault"}
        expected['Disabled'] = {"Resetting"}
        assert self.o._allowed == expected
        possible_states = [
            'Ready', 'Resetting', 'Saving', 'Loading', 'Configuring', 'Armed',
            'Running', 'Seeking', 'PostRun', 'Paused', 'Aborting', 'Aborted',
            'Fault', 'Disabling', 'Disabled']
        assert self.o.possible_states == possible_states


class TestRunnableController(unittest.TestCase):
    def setUp(self):
        self.p = Process('process1')
        self.context = Context(self.p)

        # Make a ticker_block block to act as our child
        self.c_child = call_with_params(
            ticker_block, self.p, mri="childBlock", config_dir="/tmp")
        self.b_child = self.context.block_view("childBlock")

        # Make an empty part for our parent
        part1 = Part("part1")

        # Make a RunnableChildPart to control the ticker_block
        part2 = call_with_params(
            RunnableChildPart, mri='childBlock', name='part2')

        # create a root block for the RunnableController block to reside in
        self.c = call_with_params(RunnableController, self.p, [part1, part2],
                                  mri='mainBlock', config_dir="/tmp",
                                  axesToMove=["x"])
        self.p.add_controller('mainBlock', self.c)
        self.b = self.context.block_view("mainBlock")
        self.ss = self.c.stateSet

        # start the process off
        self.checkState(self.ss.DISABLED)
        self.p.start()
        self.checkState(self.ss.READY)

    def tearDown(self):
        self.p.stop(timeout=1)

    def checkState(self, state, child=True, parent=True):
        if child:
            assert self.c_child.state.value == state
        if parent:
            assert self.c.state.value == state

    def checkSteps(self, configured, completed, total):
        assert self.b.configuredSteps.value == configured
        assert self.b.completedSteps.value == completed
        assert self.b.totalSteps.value == total
        assert self.b_child.configuredSteps.value == configured
        assert self.b_child.completedSteps.value == completed
        assert self.b_child.totalSteps.value == total

    def test_init(self):
        assert self.c.completed_steps.value == 0
        assert self.c.configured_steps.value == 0
        assert self.c.total_steps.value == 0
        assert self.c.axes_to_move.value == ("x",)
        assert list(self.b.configure.takes.elements) == \
               ["generator", "axesToMove", "exceptionStep"]

    def test_reset(self):
        self.c.disable()
        self.checkState(self.ss.DISABLED)
        self.c.reset()
        self.checkState(self.ss.READY)

    def test_set_axes_to_move(self):
        self.c.set_axes_to_move(['y'])
        assert self.c.axes_to_move.value == ('y',)

    def test_modify_child(self):
        # Save an initial setting for the child
        self.b_child.save("init_child")
        assert self.b_child.modified.value is False
        x = self.context.block_view("COUNTERX")
        x.counter.put_value(31)
        # x counter now at 31, child should be modified
        assert x.counter.value == 31
        assert self.b_child.modified.value is True
        assert self.b_child.modified.alarm.severity == AlarmSeverity.MINOR_ALARM
        assert self.b_child.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b_child.modified.alarm.message == \
            "x.counter.value = 31.0 not 0.0"
        self.prepare_half_run()
        self.b.__call__()
        # x counter now at 2, child should be modified by us
        assert self.b_child.modified.value is True
        assert self.b_child.modified.alarm.severity == AlarmSeverity.NO_ALARM
        assert self.b_child.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b_child.modified.alarm.message == \
            "(We modified) x.counter.value = 2.0 not 0.0"
        assert x.counter.value == 2.0
        x.counter.put_value(0.0)
        # x counter now at 0, child should be unmodified
        assert x.counter.value == 0
        assert self.b_child.modified.alarm.message == ""
        assert self.b_child.modified.value is False

    def test_modify_parent(self):
        # Save an initial setting for child and parent
        self.b_child.save("init_child")
        self.b.save("init_parent")
        # Change a value and save as a new child setting
        x = self.context.block_view("COUNTERX")
        x.counter.put_value(31)
        self.b_child.save("new_child")
        assert self.b_child.modified.value is False
        assert self.b.modified.value is True
        assert self.b.modified.alarm.severity == AlarmSeverity.MINOR_ALARM
        assert self.b.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b.modified.alarm.message == \
            "part2.design.value = 'new_child' not 'init_child'"
        # Do a configure, and check we get set back
        self.prepare_half_run()
        assert self.b_child.design.value == "init_child"
        assert self.b_child.modified.value is False
        assert self.b.modified.value is False

    def test_validate(self):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        actual = self.b.validate(generator=compound, axesToMove=['x'])
        assert actual["generator"].to_dict() == compound.to_dict()
        assert actual["axesToMove"] == ('x',)

    def prepare_half_run(self, duration=0.01, exception=0):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration)
        self.b.configure(
            generator=compound, axesToMove=['x'], exceptionStep=exception)

    def test_configure_run(self):
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.ss.ARMED)

        self.b.__call__()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.__call__()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.__call__()
        self.checkState(self.ss.READY)

    def test_abort(self):
        self.prepare_half_run()
        self.b.__call__()
        self.b.abort()
        self.checkState(self.ss.ABORTED)

    def test_pause_seek_resume(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)
        self.b.__call__()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        self.b.pause(completedSteps=1)
        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 1, 6)
        self.b.__call__()
        self.checkSteps(4, 2, 6)
        self.b.completedSteps.put_value(5)
        self.checkSteps(6, 5, 6)
        self.b.__call__()
        self.checkState(self.ss.READY)

    def test_resume_in_run(self):
        self.prepare_half_run(duration=0.5)
        f = self.b.run_async()
        self.context.sleep(0.95)
        self.b.pause()
        self.checkState(self.ss.PAUSED)
        self.checkSteps(2, 1, 6)
        self.b.resume()
        # Parent should be running, child won't have got request yet
        then = time.time()
        self.checkState(self.ss.RUNNING, child=False)
        self.context.wait_all_futures(f, timeout=2)
        now = time.time()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        # This test fails on Travis sometimes, looks like the docker container
        # just gets starved
        #self.assertAlmostEqual(now - then, 0.5, delta=0.1)

    def test_run_exception(self):
        self.prepare_half_run(exception=1)
        with self.assertRaises(ResponseError):
            self.b.__call__()
        self.checkState(self.ss.FAULT)

    def test_run_stop(self):
        self.prepare_half_run(duration=0.1)
        f = self.b.run_async()
        self.context.sleep(0.1)
        self.b.abort()
        with self.assertRaises(ResponseError):
            f.result()
        self.checkState(self.ss.ABORTED)


class PartTester1(Part):

    @RunnableController.Configure
    @method_takes(
        "size", StringMeta("Size of the thing"), REQUIRED)
    def configure(self, params):
        pass


class PartTester2(Part):

    def configure(self):
        pass


class PartTester3(Part):

    @RunnableController.Configure
    def configure(self):
        pass


class PartTester4(Part):

    @RunnableController.Configure
    @method_takes()
    def configure(self):
        pass


class RunnableControllerTester(RunnableController):

    def __init__(self, process, parts, params):
        super(RunnableControllerTester, self).__init__(process, parts, params)

        self.add_part(PartTester1("1"))
        self.add_part(PartTester2("2"))


class TestRunnableControllerCollectsAllParams(unittest.TestCase):

    def setUp(self):
        self.p = Process('process1')
        self.context = Context(self.p)

    def tearDown(self):
        self.p.stop(timeout=1)

    def test_no_hook_passes(self):
        # create a root block for the RunnableController block to reside in
        self.c = call_with_params(RunnableController, self.p,
                                  [PartTester1("1"), PartTester2("2")],
                                  mri='mainBlock', config_dir="/tmp",
                                  axesToMove=["x"])
        self.p.add_controller('mainBlock', self.c)
        self.b = self.context.block_view("mainBlock")

        # start the process off
        self.p.start()

        takes = list(self.b.configure.takes.elements)
        self.assertEqual(takes, ["size", "generator", "axesToMove"])

    def test_hook_fails(self):
        # create a root block for the RunnableController block to reside in
        self.c = call_with_params(RunnableController, self.p,
                                  [PartTester1("1"), PartTester3("2")],
                                  mri='mainBlock', config_dir="/tmp",
                                  axesToMove=["x"])
        self.p.add_controller('mainBlock', self.c)
        self.b = self.context.block_view("mainBlock")

        # start the process off
        self.p.start()

        takes = list(self.b.configure.takes.elements)
        self.assertEqual(takes, ["size", "generator", "axesToMove"])

    def test_hook_plus_method_takes_nothing_passes(self):
        # create a root block for the RunnableController block to reside in
        self.c = call_with_params(RunnableController, self.p,
                                  [PartTester1("1"), PartTester4("2")],
                                  mri='mainBlock', config_dir="/tmp",
                                  axesToMove=["x"])
        self.p.add_controller('mainBlock', self.c)
        self.b = self.context.block_view("mainBlock")

        # start the process off
        self.p.start()

        takes = list(self.b.configure.takes.elements)
        self.assertEqual(takes, ["size", "generator", "axesToMove"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
