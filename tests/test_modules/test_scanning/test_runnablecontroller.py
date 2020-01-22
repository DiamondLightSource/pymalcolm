import unittest
import time

from scanpointgenerator import LineGenerator, CompoundGenerator, \
    ConcatGenerator, StaticPointGenerator
from annotypes import add_call_types

from malcolm.modules.demo.parts.motionchildpart import AExceptionStep
from malcolm.modules.scanning.hooks import ACompletedSteps, AContext, \
    AStepsToDo, ValidateHook, UInfos, AAxesToMove, AGenerator
from malcolm.core import Process, Context, AlarmStatus, \
    AlarmSeverity, AbortedError
from malcolm.modules.demo.parts import MotionChildPart
from malcolm.modules.demo.blocks import motion_block
from malcolm.compat import OrderedDict
from malcolm.modules.scanning.controllers import \
    RunnableController, get_steps_per_run
from malcolm.modules.scanning.infos import ParameterTweakInfo
from malcolm.modules.scanning.util import RunnableStates


class MisbehavingPauseException(Exception):
    pass


class MisbehavingPart(MotionChildPart):
    def setup(self, registrar):
        super(MisbehavingPart, self).setup(registrar)
        self.register_hooked(ValidateHook, self.validate)

    @add_call_types
    def validate(self, generator):
        # type: (AGenerator) -> UInfos
        if generator.duration < 0.1:
            serialized = generator.to_dict()
            new_generator = CompoundGenerator.from_dict(serialized)
            new_generator.duration = 0.1
            return ParameterTweakInfo("generator", new_generator)

    # Allow CamelCase for arguments as they will be serialized by parent
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(self,
                     context,  # type: AContext
                     completed_steps,  # type: ACompletedSteps
                     steps_to_do,  # type: AStepsToDo
                     # The following were passed from the user calling configure()
                     generator,  # type: AGenerator
                     axesToMove,  # type: AAxesToMove
                     exceptionStep=0,  # type: AExceptionStep
                     ):
        # type: (...) -> None
        super(MisbehavingPart, self).on_configure(
            context, completed_steps, steps_to_do, generator, axesToMove,
            exceptionStep)
        if completed_steps == 3:
            raise MisbehavingPauseException("Called magic number to make pause throw an exception")


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
        expected['PostRun'] = {"Finished", "Armed", "Seeking", "Aborting", "Fault",
                               "Disabling"}
        expected['Finished'] = {"Seeking", "Resetting", "Configuring", "Aborting", "Fault",
                               "Disabling"}
        expected['Seeking'] = {"Armed", "Paused", "Finished", "Aborting", "Fault",
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
            'Running', 'Seeking', 'PostRun', 'Finished', 'Paused', 'Aborting', 'Aborted',
            'Fault', 'Disabling', 'Disabled']
        assert self.o.possible_states == possible_states


class TestRunnableController(unittest.TestCase):
    def setUp(self):
        self.p = Process('process1')
        self.context = Context(self.p)

        self.p2 = Process('process2')
        self.context2 = Context(self.p2)

        # Make a motion block to act as our child
        for c in motion_block(mri="childBlock", config_dir="/tmp"):
            self.p.add_controller(c)
        self.b_child = self.context.block_view("childBlock")

        # Make a RunnableChildPart to control the ticker_block
        # part2 = RunnableChildPart(
        #     mri='childBlock', name='part2', initial_visibility=True)

        part = MisbehavingPart(
            mri='childBlock', name='part2', initial_visibility=True)

        # create a root block for the RunnableController block to reside in
        self.c = RunnableController(mri='mainBlock', config_dir="/tmp")
        self.c.add_part(part)
        self.p.add_controller(self.c)
        self.b = self.context.block_view("mainBlock")
        self.ss = self.c.state_set

        # start the process off
        self.checkState(self.ss.DISABLED)
        self.p.start()
        self.checkState(self.ss.READY)

    def tearDown(self):
        self.p.stop(timeout=1)

    def checkState(self, state):
        assert self.c.state.value == state

    def checkSteps(self, configured, completed, total):
        assert self.b.configuredSteps.value == configured
        assert self.b.completedSteps.value == completed
        assert self.b.totalSteps.value == total

    def test_init(self):
        assert self.c.completed_steps.value == 0
        assert self.c.configured_steps.value == 0
        assert self.c.total_steps.value == 0
        assert list(self.b.configure.meta.takes.elements) == \
               ["generator", "axesToMove", "breakpoints", "exceptionStep"]

    def test_reset(self):
        self.c.disable()
        self.checkState(self.ss.DISABLED)
        self.c.reset()
        self.checkState(self.ss.READY)

    def test_modify_child(self):
        # Save an initial setting for the child
        self.b_child.save("init_child")
        assert self.b_child.modified.value is False
        x = self.context.block_view("childBlock:COUNTERX")
        x.delta.put_value(31)
        # x delta now at 31, child should be modified
        assert x.delta.value == 31
        assert self.b_child.modified.value is True
        assert self.b_child.modified.alarm.severity == AlarmSeverity.MINOR_ALARM
        assert self.b_child.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b_child.modified.alarm.message == \
            "x.delta.value = 31.0 not 1.0"
        self.prepare_half_run()
        self.b.run()
        # x counter now at 3 (lower bound of first run of x in reverse),
        # child should still be modified
        assert self.b_child.modified.value is True
        assert self.b_child.modified.alarm.severity == AlarmSeverity.MINOR_ALARM
        assert self.b_child.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b_child.modified.alarm.message == \
            "x.delta.value = 31.0 not 1.0"
        assert x.counter.value == 3.0
        assert x.delta.value == 31
        x.delta.put_value(1.0)
        # x counter now at 0, child should be unmodified
        assert x.delta.value == 1.0
        assert self.b_child.modified.alarm.message == ""
        assert self.b_child.modified.value is False

    def test_modify_parent(self):
        # Save an initial setting for child and parent
        self.b_child.save("init_child")
        self.b.save("init_parent")
        # Change a value and save as a new child setting
        x = self.context.block_view("childBlock:COUNTERX")
        x.counter.put_value(31)
        self.b_child.save("new_child")
        assert self.b_child.modified.value is False
        assert self.b.modified.value is True
        assert self.b.modified.alarm.severity == AlarmSeverity.MINOR_ALARM
        assert self.b.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b.modified.alarm.message == \
            "part2.design.value = 'new_child' not 'init_child'"
        # Load the child again
        self.b_child.design.put_value("new_child")
        assert self.b.modified.value is True
        # And check that loading parent resets it
        self.b.design.put_value("init_parent")
        assert self.b.modified.value is False
        assert self.b_child.design.value == "init_child"
        # Put back
        self.b_child.design.put_value("new_child")
        assert self.b.modified.value is True
        # Do a configure, and check we get set back
        self.prepare_half_run()
        assert self.b_child.design.value == "init_child"
        assert self.b_child.modified.value is False
        assert self.b.modified.value is False

    def test_abort(self):
        self.b.abort()
        self.checkState(self.ss.ABORTED)

    def test_validate(self):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration=0.001)
        actual = self.b.validate(generator=compound, axesToMove=['x'])
        assert actual["generator"].duration == 0.1
        actual["generator"].duration = 0.001
        assert actual["generator"].to_dict() == compound.to_dict()
        assert actual["axesToMove"] == ['x']

    def prepare_half_run(self, duration=0.01, exception=0):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2, alternate=True)
        compound = CompoundGenerator([line1, line2], [], [], duration)
        self.b.configure(
            generator=compound, axesToMove=['x'], exceptionStep=exception)

    def test_configure_run(self):
        assert self.b.configure.meta.writeable is True
        assert self.b.configure.meta.takes.elements["generator"].writeable is True
        assert self.b.validate.meta.takes.elements["generator"].writeable is True
        assert self.b.validate.meta.returns.elements["generator"].writeable is False
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.ss.ARMED)
        assert self.b.configure.meta.writeable is False
        assert self.b.configure.meta.takes.elements["generator"].writeable is True
        assert self.b.validate.meta.takes.elements["generator"].writeable is True
        assert self.b.validate.meta.returns.elements["generator"].writeable is False

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_abort(self):
        self.prepare_half_run()
        self.b.run()
        self.b.abort()
        self.checkState(self.ss.ABORTED)

    def test_pause_seek_resume(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)
        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        self.b.pause(lastGoodStep=1)
        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 1, 6)
        self.b.run()
        self.checkSteps(4, 2, 6)
        self.b.completedSteps.put_value(5)
        self.checkSteps(6, 5, 6)
        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_pause_seek_resume_outside_limits(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)
        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        self.b.pause(lastGoodStep=7)
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 5, 6)
        self.b.run()
        self.checkState(self.ss.FINISHED)

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
        self.checkState(self.ss.RUNNING)
        self.context.wait_all_futures(f, timeout=2)
        now = time.time()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        # This test fails on Travis sometimes, looks like the docker container
        # just gets starved
        # self.assertAlmostEqual(now - then, 0.5, delta=0.1)

    def test_pause_seek_resume_from_finished(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

        self.b.pause(lastGoodStep=1)
        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 1, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_pause_seek_resume_from_postrun(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

        self.b.pause(lastGoodStep=1)
        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 1, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_reset_from_finished(self):
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

        self.c.reset()
        self.checkState(self.ss.READY)

    def test_configure_from_finished(self):
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_run_exception(self):
        self.prepare_half_run(exception=1)
        with self.assertRaises(AssertionError):
            self.b.run()
        self.checkState(self.ss.FAULT)

    def test_run_stop(self):
        self.prepare_half_run(duration=0.1)
        f = self.b.run_async()
        self.context.sleep(0.1)
        self.b.abort()
        with self.assertRaises(AbortedError):
            f.result()
        self.checkState(self.ss.ABORTED)

    def test_error_in_pause_returns_run(self):
        self.prepare_half_run(duration=0.5)
        f = self.b.run_async()
        self.context.sleep(0.95)
        with self.assertRaises(MisbehavingPauseException):
            self.b.pause(lastGoodStep=3)
        self.checkState(self.ss.FAULT)
        with self.assertRaises(AbortedError):
            f.result()

    def test_breakpoints_tomo(self):
        line1 = LineGenerator('x', 'mm', -10, -10, 5)
        line2 = LineGenerator('x', 'mm', 0, 180, 10)
        line3 = LineGenerator('x', 'mm', 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        breakpoints = [2, 3, 10, 2]
        self.b.configure(generator=CompoundGenerator([concat],
                         [], [], duration),
                         axesToMove=['x'],
                         breakpoints=breakpoints,
                         exceptionStep=0)

        assert self.c.configure_params.generator.size == 17
        self.checkSteps(2, 0, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(5, 2, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 17, 17)
        self.checkState(self.ss.FINISHED)

        pass

    def test_steps_per_run_one_axis(self):
        line = LineGenerator('x', 'mm', 0, 180, 10)
        duration = 0.01
        compound = CompoundGenerator([line], [], [], duration)
        compound.prepare()

        steps_per_run = get_steps_per_run(compound, ['x'], [])
        assert steps_per_run[0] == 10

    def test_steps_per_run(self):
        line1 = LineGenerator('x', 'mm', -10, -10, 5)
        line2 = LineGenerator('x', 'mm', 0, 180, 10)
        line3 = LineGenerator('x', 'mm', 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        compound = CompoundGenerator([concat], [], [], duration)
        compound.prepare()
        breakpoints = [2, 3, 10, 2]

        steps_per_run = get_steps_per_run(
            generator=compound,
            axes_to_move=['x'],
            breakpoints=breakpoints)
        assert steps_per_run == breakpoints

    def test_breakpoints_without_last(self):
        line1 = LineGenerator('x', 'mm', -10, -10, 5)
        line2 = LineGenerator('x', 'mm', 0, 180, 10)
        line3 = LineGenerator('x', 'mm', 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        breakpoints = [2, 3, 10]
        self.b.configure(generator=CompoundGenerator([concat],
                         [], [], duration),
                         axesToMove=['x'],
                         breakpoints=breakpoints,
                         exceptionStep=0)

        assert self.c.configure_params.generator.size == 17
        self.checkSteps(2, 0, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(5, 2, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 17, 17)
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_rocking_tomo(self):
        line1 = LineGenerator('x', 'mm', -10, -10, 5)
        line2 = LineGenerator('x', 'mm', 0, 180, 10)
        line3 = LineGenerator('x', 'mm', 190, 190, 2)
        line4 = LineGenerator('x', 'mm', 180, 0, 10)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3, line4])
        breakpoints = [2, 3, 10, 2]
        self.b.configure(generator=CompoundGenerator([concat],
                         [], [], duration),
                         axesToMove=['x'],
                         breakpoints=breakpoints,
                         exceptionStep=0)

        assert self.c.configure_params.generator.size == 27
        self.checkSteps(2, 0, 27)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(5, 2, 27)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 27)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 27)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(27, 17, 27)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(27, 27, 27)
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_repeat_with_static(self):
        line1 = LineGenerator('x', 'mm', -10, -10, 5)
        line2 = LineGenerator('x', 'mm', 0, 180, 10)
        line3 = LineGenerator('x', 'mm', 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])

        staticGen = StaticPointGenerator(2)
        breakpoints = [2, 3, 10, 2, 2, 3, 10, 2]

        self.b.configure(generator=CompoundGenerator([staticGen, concat],
                         [], [], duration),
                         axesToMove=['x'],
                         breakpoints=breakpoints)

        assert self.c.configure_params.generator.size == 34

        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 0, 34)

        self.b.run()
        self.checkSteps(5, 2, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(19, 17, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(22, 19, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(32, 22, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(34, 32, 34)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_repeat_rocking_tomo(self):
        line1 = LineGenerator('x', 'mm', -10, -10, 5)
        line2 = LineGenerator('x', 'mm', 0, 180, 10)
        line3 = LineGenerator('x', 'mm', 190, 190, 2)
        line4 = LineGenerator('x', 'mm', 180, 0, 10)
        concat = ConcatGenerator([line1, line2, line3, line4])

        staticGen = StaticPointGenerator(2)

        duration = 0.01
        breakpoints = [2, 3, 10, 2, 10, 2, 3, 10, 2, 10]
        self.b.configure(generator=CompoundGenerator([staticGen, concat],
                         [], [], duration),
                         axesToMove=['x'],
                         breakpoints=breakpoints)

        assert self.c.configure_params.generator.size == 54

        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 0, 54)

        self.b.run()
        self.checkSteps(5, 2, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(27, 17, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(29, 27, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(32, 29, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(42, 32, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(44, 42, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(54, 44, 54)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_helical_scan(self):
        line1 = LineGenerator(['y','x'], ['mm','mm'],
                              [-0.555556, -10], [-0.555556, -10], 5)
        line2 = LineGenerator(['y','x'], ['mm','mm'], [0, 0], [10, 180], 10)
        line3 = LineGenerator(['y','x'], ['mm','mm'],
                              [10.555556, 190], [10.555556, 190], 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])

        breakpoints = [2, 3, 10, 2]
        self.b.configure(generator=CompoundGenerator([concat],
                         [], [], duration),
                         axesToMove=['y','x'],
                         breakpoints=breakpoints)

        self.c.configure_params.generator.size == 17

        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 0, 17)

        self.b.run()
        self.checkSteps(5, 2, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.FINISHED)
