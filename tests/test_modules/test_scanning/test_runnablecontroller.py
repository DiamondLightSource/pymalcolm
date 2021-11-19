import shutil
import unittest
from typing import Optional

import cothread
import numpy as np
import pytest
from annotypes import Anno, add_call_types
from scanpointgenerator import (
    CompoundGenerator,
    ConcatGenerator,
    LineGenerator,
    StaticPointGenerator,
)

from malcolm.compat import OrderedDict
from malcolm.core import (
    AbortedError,
    AlarmSeverity,
    AlarmStatus,
    Context,
    PartRegistrar,
    Process,
)
from malcolm.modules import builtin, scanning
from malcolm.modules.builtin.defines import tmp_dir
from malcolm.modules.demo.blocks import detector_block, motion_block
from malcolm.modules.demo.parts import MotionChildPart
from malcolm.modules.demo.parts.motionchildpart import AExceptionStep
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.hooks import (
    AAxesToMove,
    ABreakpoints,
    ACompletedSteps,
    AContext,
    AGenerator,
    AStepsToDo,
    PreRunHook,
    UInfos,
    ValidateHook,
)
from malcolm.modules.scanning.infos import ParameterTweakInfo
from malcolm.modules.scanning.parts import DetectorChildPart
from malcolm.modules.scanning.util import DetectorTable, RunnableStates

APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility
AStateful = builtin.parts.AStateful

with Anno("Value to tweak duration to in Validate"):
    AValidateDuration = float


class MisbehavingPauseException(Exception):
    pass


class MisbehavingPart(MotionChildPart):
    def __init__(
        self,
        name: APartName,
        mri: AMri,
        initial_visibility: AInitialVisibility = False,
        stateful: AStateful = True,
        validate_duration: AValidateDuration = 0.5,
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=stateful
        )
        self.validate_duration = validate_duration

    def setup(self, registrar):
        super(MisbehavingPart, self).setup(registrar)
        self.register_hooked(ValidateHook, self.validate)
        self.register_hooked(PreRunHook, self.on_pre_run)

    @add_call_types
    def validate(self, generator: AGenerator) -> UInfos:
        # Always tweak to the same value
        if generator.duration != self.validate_duration:
            serialized = generator.to_dict()
            new_generator = CompoundGenerator.from_dict(serialized)
            new_generator.duration = self.validate_duration
            return ParameterTweakInfo("generator", new_generator)
        else:
            return None

    @add_call_types
    def on_pre_run(self):
        self.pre_run_test = True

    # Allow CamelCase for arguments as they will be serialized by parent
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: AContext,
        completed_steps: ACompletedSteps,
        steps_to_do: AStepsToDo,
        # The following were passed from the user calling configure()
        generator: AGenerator,
        axesToMove: AAxesToMove,
        breakpoints: ABreakpoints,
        exceptionStep: AExceptionStep = 0,
    ) -> None:
        super(MisbehavingPart, self).on_configure(
            context, completed_steps, steps_to_do, generator, axesToMove, exceptionStep
        )
        if completed_steps == 3:
            raise MisbehavingPauseException(
                "Called magic number to make pause throw an exception"
            )


class RunForeverPart(builtin.parts.ChildPart):
    """Part which runs forever and takes 1s to abort"""

    def setup(self, registrar: PartRegistrar) -> None:
        super(RunForeverPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(scanning.hooks.AbortHook, self.on_abort)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # Wait forever here
        while True:
            context.sleep(1.0)

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext) -> None:
        # Sleep for 1s before returning
        context.sleep(1.0)


class TestRunnableStates(unittest.TestCase):
    def setUp(self):
        self.o = RunnableStates()

    def test_init(self):
        expected = OrderedDict()
        expected["Resetting"] = {"Ready", "Fault", "Disabling"}
        expected["Ready"] = {
            "Configuring",
            "Aborting",
            "Saving",
            "Fault",
            "Disabling",
            "Loading",
        }
        expected["Saving"] = {"Fault", "Ready", "Disabling"}
        expected["Loading"] = {"Disabling", "Fault", "Ready"}
        expected["Configuring"] = {"Armed", "Aborting", "Fault", "Disabling"}
        expected["Armed"] = {
            "Seeking",
            "Aborting",
            "Running",
            "Fault",
            "Disabling",
            "Resetting",
        }
        expected["Running"] = {"PostRun", "Seeking", "Aborting", "Fault", "Disabling"}
        expected["PostRun"] = {
            "Finished",
            "Armed",
            "Seeking",
            "Aborting",
            "Fault",
            "Disabling",
        }
        expected["Finished"] = {
            "Seeking",
            "Resetting",
            "Configuring",
            "Aborting",
            "Fault",
            "Disabling",
        }
        expected["Seeking"] = {
            "Armed",
            "Paused",
            "Finished",
            "Aborting",
            "Fault",
            "Disabling",
        }
        expected["Paused"] = {"Seeking", "Running", "Aborting", "Fault", "Disabling"}
        expected["Aborting"] = {"Aborted", "Fault", "Disabling"}
        expected["Aborted"] = {"Resetting", "Fault", "Disabling"}
        expected["Fault"] = {"Resetting", "Disabling"}
        expected["Disabling"] = {"Disabled", "Fault"}
        expected["Disabled"] = {"Resetting"}
        assert self.o._allowed == expected
        possible_states = [
            "Ready",
            "Resetting",
            "Saving",
            "Loading",
            "Configuring",
            "Armed",
            "Running",
            "Seeking",
            "PostRun",
            "Finished",
            "Paused",
            "Aborting",
            "Aborted",
            "Fault",
            "Disabling",
            "Disabled",
        ]
        assert self.o.possible_states == possible_states


class TestRunnableController(unittest.TestCase):
    def setUp(self):
        self.p = Process("process")
        self.context = Context(self.p)

        # Make a motion block to act as our child
        self.config_dir = tmp_dir("config_dir")
        for c in motion_block(mri="childBlock", config_dir=self.config_dir.value):
            self.p.add_controller(c)
        self.b_child = self.context.block_view("childBlock")

        self.part = MisbehavingPart(
            mri="childBlock", name="part", initial_visibility=True
        )

        # create a root block for the RunnableController block to reside in
        self.c = RunnableController(mri="mainBlock", config_dir=self.config_dir.value)
        self.c.add_part(self.part)
        self.p.add_controller(self.c)
        self.b = self.context.block_view("mainBlock")
        self.ss = self.c.state_set

        # start the process off
        self.checkState(self.ss.DISABLED)
        self.p.start()
        self.checkState(self.ss.READY)

    def tearDown(self):
        self.p.stop(timeout=1)
        shutil.rmtree(self.config_dir.value)

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
        assert list(self.b.configure.meta.takes.elements) == [
            "generator",
            "axesToMove",
            "breakpoints",
            "exceptionStep",
        ]

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
        assert self.b_child.modified.alarm.message == "x.delta.value = 31.0 not 1.0"
        self.prepare_half_run()
        self.b.run()
        # x counter now at 3 (lower bound of first run of x in reverse),
        # child should still be modified
        assert self.b_child.modified.value is True
        assert self.b_child.modified.alarm.severity == AlarmSeverity.MINOR_ALARM
        assert self.b_child.modified.alarm.status == AlarmStatus.CONF_STATUS
        assert self.b_child.modified.alarm.message == "x.delta.value = 31.0 not 1.0"
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
        assert (
            self.b.modified.alarm.message
            == "part.design.value = 'new_child' not 'init_child'"
        )
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

    def prepare_half_run(self, duration=0.01, exception=0):
        line1 = LineGenerator("y", "mm", 0, 2, 3)
        line2 = LineGenerator("x", "mm", 0, 2, 2, alternate=True)
        compound = CompoundGenerator([line1, line2], [], [], duration)
        self.b.configure(generator=compound, axesToMove=["x"], exceptionStep=exception)

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

    def test_abort_during_run(self):
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

    def test_pause_seek_resume_at_boundaries_without_defined_lastGoodStep(self):
        # When pausing at boundaries without lastGoodStep the scan should
        # remain in the same state - Armed for the start of the next inner scan
        # or Finished if the scan is complete.
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)

        self.b.pause()
        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 0, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        self.b.pause()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)
        self.b.pause()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.FINISHED)
        self.b.pause()
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
        # then = time.time()
        self.checkState(self.ss.RUNNING)
        self.context.wait_all_futures(f, timeout=2)
        # now = time.time()
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

    def test_prerun_gets_called(self):
        self.prepare_half_run()
        self.b.run()
        assert self.part.pre_run_test


class TestRunnableControllerBreakpoints(unittest.TestCase):
    def setUp(self):
        self.p = Process("process1")
        self.context = Context(self.p)

        self.p2 = Process("process2")
        self.context2 = Context(self.p2)

        # Make a motion block to act as our child
        self.config_dir = tmp_dir("config_dir")
        for c in motion_block(mri="childBlock", config_dir=self.config_dir.value):
            self.p.add_controller(c)
        self.b_child = self.context.block_view("childBlock")

        # create a root block for the RunnableController block to reside in
        self.c = RunnableController(mri="mainBlock", config_dir=self.config_dir.value)
        self.p.add_controller(self.c)
        self.b = self.context.block_view("mainBlock")
        self.ss = self.c.state_set

        # start the process off
        self.checkState(self.ss.DISABLED)
        self.p.start()
        self.checkState(self.ss.READY)

    def tearDown(self):
        self.p.stop(timeout=1)
        shutil.rmtree(self.config_dir.value)

    def checkState(self, state):
        assert self.c.state.value == state

    def checkSteps(self, configured, completed, total):
        assert self.b.configuredSteps.value == configured
        assert self.b.completedSteps.value == completed
        assert self.b.totalSteps.value == total

    def test_get_breakpoint_index(self):
        line = LineGenerator("x", "mm", 0, 180, 100)
        duration = 0.01
        breakpoints = [10, 20, 30, 40]

        self.b.configure(
            generator=CompoundGenerator([line], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

        test_steps = [0, 5, 10, 20, 30, 40, 60, 80, 100]

        expected_indices = [0, 0, 1, 1, 2, 2, 3, 3, 3]

        # Check the breakpoint_steps are set as expected
        assert self.c.breakpoint_steps == [10, 30, 60, 100]

        for step_num in range(len(test_steps)):
            steps = test_steps[step_num]
            index = expected_indices[step_num]
            actual_index = self.c.get_breakpoint_index(steps)
            assert (
                actual_index == index
            ), f"Expected index {index} for {steps} steps, got {actual_index}"

    def test_steps_per_run_one_axis(self):
        line = LineGenerator("x", "mm", 0, 180, 10)
        duration = 0.01
        compound = CompoundGenerator([line], [], [], duration)
        compound.prepare()

        steps_per_run = self.c.get_steps_per_run(
            generator=compound, axes_to_move=["x"], breakpoints=[]
        )
        assert steps_per_run == [10]

    def test_steps_per_run_concat(self):
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        compound = CompoundGenerator([concat], [], [], duration)
        compound.prepare()
        breakpoints = [2, 3, 10, 2]

        steps_per_run = self.c.get_steps_per_run(
            generator=compound, axes_to_move=["x"], breakpoints=breakpoints
        )
        assert steps_per_run == breakpoints

    def test_breakpoints_tomo(self):
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        breakpoints = [2, 3, 10, 2]
        self.b.configure(
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

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

    def test_breakpoints_sum_larger_than_total_steps_raises_AssertionError(self):
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])

        breakpoints = [2, 3, 100, 2]

        self.assertRaises(
            AssertionError,
            self.b.configure,
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

    def test_breakpoints_without_last(self):
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        breakpoints = [2, 3, 10]
        self.b.configure(
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

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
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        line4 = LineGenerator("x", "mm", 180, 0, 10)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3, line4])
        breakpoints = [2, 3, 10, 2]
        self.b.configure(
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

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
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])

        staticGen = StaticPointGenerator(2)
        breakpoints = [2, 3, 10, 2, 2, 3, 10, 2]

        self.b.configure(
            generator=CompoundGenerator([staticGen, concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

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
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        line4 = LineGenerator("x", "mm", 180, 0, 10)
        concat = ConcatGenerator([line1, line2, line3, line4])

        staticGen = StaticPointGenerator(2)

        duration = 0.01
        breakpoints = [2, 3, 10, 2, 10, 2, 3, 10, 2, 10]
        self.b.configure(
            generator=CompoundGenerator([staticGen, concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

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
        line1 = LineGenerator(
            ["y", "x"], ["mm", "mm"], [-0.555556, -10], [-0.555556, -10], 5
        )
        line2 = LineGenerator(["y", "x"], ["mm", "mm"], [0, 0], [10, 180], 10)
        line3 = LineGenerator(
            ["y", "x"], ["mm", "mm"], [10.555556, 190], [10.555556, 190], 2
        )
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])

        breakpoints = [2, 3, 10, 2]
        self.b.configure(
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["y", "x"],
            breakpoints=breakpoints,
        )

        assert self.c.configure_params.generator.size == 17

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

    def test_breakpoints_with_pause(self):
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        breakpoints = [2, 3, 10, 2]
        self.b.configure(
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

        assert self.c.configure_params.generator.size == 17

        self.checkSteps(2, 0, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(5, 2, 17)
        self.checkState(self.ss.ARMED)

        # rewind
        self.b.pause(lastGoodStep=1)
        self.checkSteps(2, 1, 17)
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

        # rewind
        self.b.pause(lastGoodStep=11)
        self.checkSteps(15, 11, 17)
        self.checkState(self.ss.ARMED)
        self.b.run()
        self.checkSteps(17, 15, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 17, 17)
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_with_pause_at_boundaries_without_lastGoodStep(self):
        # We expect the pause call to be successful but not to have an effect
        # when called at a breakpoint or at the end of a scan.
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])
        breakpoints = [2, 3, 10, 2]
        self.b.configure(
            generator=CompoundGenerator([concat], [], [], duration),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

        assert self.c.configure_params.generator.size == 17

        self.checkSteps(2, 0, 17)
        self.checkState(self.ss.ARMED)
        # Pause
        self.b.pause()
        self.checkSteps(2, 0, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(5, 2, 17)
        self.checkState(self.ss.ARMED)
        # Pause
        self.b.pause()
        self.checkSteps(5, 2, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(15, 5, 17)
        self.checkState(self.ss.ARMED)
        # Pause
        self.b.pause()
        self.checkSteps(15, 5, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 15, 17)
        self.checkState(self.ss.ARMED)
        # Pause
        self.b.pause()
        self.checkSteps(17, 15, 17)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkSteps(17, 17, 17)
        self.checkState(self.ss.FINISHED)
        # Pause
        self.b.pause()
        self.checkSteps(17, 17, 17)
        self.checkState(self.ss.FINISHED)

    def abort_after_1s(self):
        # Need a new context as in a different cothread
        c = Context(self.p)
        b = c.block_view("mainBlock")
        c.sleep(1.0)
        self.checkState(self.ss.RUNNING)
        b.abort()
        self.checkState(self.ss.ABORTED)

    def test_run_returns_in_ABORTED_state_when_aborted(self):
        # Add our forever running part
        forever_part = RunForeverPart(
            mri="childBlock", name="forever_part", initial_visibility=True
        )
        self.c.add_part(forever_part)

        # Configure our block
        duration = 0.1
        line1 = LineGenerator("y", "mm", 0, 2, 3)
        line2 = LineGenerator("x", "mm", 0, 2, 2, alternate=True)
        compound = CompoundGenerator([line1, line2], [], [], duration)
        self.b.configure(generator=compound, axesToMove=["x"])

        # Spawn the abort thread
        abort_thread = cothread.Spawn(self.abort_after_1s, raise_on_wait=True)

        # Do the run, which will be aborted
        with self.assertRaises(AbortedError):
            self.b.run()

        self.checkState(self.ss.ABORTED)

        # Check the abort thread didn't raise
        abort_thread.Wait(1.0)

    def test_breakpoints_tomo_with_outer_axis(self):
        # Outer axis we don't move
        outer_steps = 2
        line_outer = LineGenerator("y", "mm", 0, 1, outer_steps)

        # ConcatGenerator we do move
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        concat = ConcatGenerator([line1, line2, line3])

        compound = CompoundGenerator([line_outer, concat], [], [], duration=0.01)
        breakpoints = [2, 3, 10, 2]
        inner_steps = sum(breakpoints)
        total_steps = inner_steps * outer_steps

        self.b.configure(generator=compound, axesToMove=["x"], breakpoints=breakpoints)
        # Configured, completed, total
        self.checkSteps(2, 0, total_steps)
        self.checkState(self.ss.ARMED)

        # Check we have the full configured steps
        assert self.c.configure_params.generator.size == total_steps

        # Check our breakpoints steps
        expected_breakpoint_steps = [2, 5, 15, 17, 19, 22, 32, 34]
        self.assertEqual(expected_breakpoint_steps, self.c.breakpoint_steps)

        # Run our controller through all but last breakpoint
        breakpoints = len(expected_breakpoint_steps)
        for index in range(breakpoints - 1):
            self.b.run()
            self.checkSteps(
                expected_breakpoint_steps[index + 1],
                expected_breakpoint_steps[index],
                total_steps,
            )
            self.checkState(self.ss.ARMED)

        # Final breakpoint
        self.b.run()
        self.checkSteps(total_steps, total_steps, total_steps)
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_tomo_with_two_outer_axes(self):
        # Outer axes we don't move
        outer_steps = 2
        line_outer = LineGenerator("y", "mm", 0, 1, outer_steps)
        outer_outer_steps = 3
        line_outer_outer = LineGenerator("z", "mm", 0, 1, outer_outer_steps)

        # ConcatGenerator we do move
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        concat = ConcatGenerator([line1, line2])

        compound = CompoundGenerator(
            [line_outer_outer, line_outer, concat], [], [], duration=0.01
        )
        breakpoints = [2, 3, 10]
        inner_steps = sum(breakpoints)
        total_steps = inner_steps * outer_steps * outer_outer_steps

        self.b.configure(generator=compound, axesToMove=["x"], breakpoints=breakpoints)
        # Configured, completed, total
        self.checkSteps(2, 0, total_steps)
        self.checkState(self.ss.ARMED)

        # Check we have the full configured steps
        assert self.c.configure_params.generator.size == total_steps

        # Check our breakpoints steps
        expected_breakpoint_steps = [
            2,
            5,
            15,
            17,
            20,
            30,
            32,
            35,
            45,
            47,
            50,
            60,
            62,
            65,
            75,
            77,
            80,
            90,
        ]
        self.assertEqual(expected_breakpoint_steps, self.c.breakpoint_steps)

        # Run our controller through all but last breakpoint
        breakpoints = len(expected_breakpoint_steps)
        for index in range(breakpoints - 1):
            self.b.run()
            self.checkSteps(
                expected_breakpoint_steps[index + 1],
                expected_breakpoint_steps[index],
                total_steps,
            )
            self.checkState(self.ss.ARMED)

        # Final breakpoint
        self.b.run()
        self.checkSteps(total_steps, total_steps, total_steps)
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_2d_inner_scan(self):
        # Y-axis
        outer_steps = 2
        line_y = LineGenerator("y", "mm", 0, 1, outer_steps)

        # X-axis
        line_x_1 = LineGenerator("x", "mm", -10, -10, 5)
        line_x_2 = LineGenerator("x", "mm", 0, 180, 10)
        line_x_3 = LineGenerator("x", "mm", 190, 190, 2)
        line_x = ConcatGenerator([line_x_1, line_x_2, line_x_3])

        compound = CompoundGenerator([line_y, line_x], [], [], duration=0.01)
        breakpoints = [2, 3, 10, 2, 17]
        total_steps = sum(breakpoints)

        # Configure the scan
        self.b.configure(
            generator=compound, axesToMove=["x", "y"], breakpoints=breakpoints
        )
        self.checkSteps(2, 0, total_steps)
        self.checkState(self.ss.ARMED)

        # Check we have the full amount of configured steps
        assert self.c.configure_params.generator.size == total_steps

        # Check our breakpoints steps
        expected_breakpoint_steps = [2, 5, 15, 17, 34]
        self.assertEqual(expected_breakpoint_steps, self.c.breakpoint_steps)

        # Run our controller through all but last breakpoint
        breakpoints = len(expected_breakpoint_steps)
        for index in range(breakpoints - 1):
            self.b.run()
            self.checkSteps(
                expected_breakpoint_steps[index + 1],
                expected_breakpoint_steps[index],
                total_steps,
            )
            self.checkState(self.ss.ARMED)

        # Final breakpoint
        self.b.run()
        self.checkSteps(total_steps, total_steps, total_steps)
        self.checkState(self.ss.FINISHED)

    def test_breakpoints_2d_inner_scan_with_outer_axis(self):
        # Outer axes we don't move
        outer_steps = 2
        line_outer = LineGenerator("z", "mm", 0, 1, outer_steps)

        # Y-axis
        line_y = LineGenerator("y", "mm", 0, 1, 2)

        # X-axis
        line_x_1 = LineGenerator("x", "mm", -10, -10, 5)
        line_x_2 = LineGenerator("x", "mm", 0, 180, 10)
        line_x_3 = LineGenerator("x", "mm", 190, 190, 2)
        line_x = ConcatGenerator([line_x_1, line_x_2, line_x_3])

        compound = CompoundGenerator(
            [line_outer, line_y, line_x], [], [], duration=0.01
        )
        breakpoints = [2, 3, 10, 2, 17]
        total_steps = sum(breakpoints) * outer_steps

        # Configure the scan
        self.b.configure(
            generator=compound, axesToMove=["x", "y"], breakpoints=breakpoints
        )
        self.checkSteps(2, 0, total_steps)
        self.checkState(self.ss.ARMED)

        # Check we have the full amount of configured steps
        assert self.c.configure_params.generator.size == total_steps

        # Check our breakpoints steps
        expected_breakpoint_steps = [2, 5, 15, 17, 34, 36, 39, 49, 51, 68]
        self.assertEqual(expected_breakpoint_steps, self.c.breakpoint_steps)

        # Run our controller through all but last breakpoint
        breakpoints = len(expected_breakpoint_steps)
        for index in range(breakpoints - 1):
            self.b.run()
            self.checkSteps(
                expected_breakpoint_steps[index + 1],
                expected_breakpoint_steps[index],
                total_steps,
            )
            self.checkState(self.ss.ARMED)

        # Final breakpoint
        self.b.run()
        self.checkSteps(total_steps, total_steps, total_steps)
        self.checkState(self.ss.FINISHED)


class TestRunnableControllerValidation(unittest.TestCase):
    """This test class is to test validation with multiple parts tweaking
    parameters"""

    def setUp(self):
        self.p = Process("process")
        self.context = Context(self.p)

        self.main_mri = "mainBlock"
        self.detector_one_mri = "detector01"
        self.detector_two_mri = "detector02"
        self.detector_one_part_name = "detectorPart01"
        self.detector_two_part_name = "detectorPart02"

        # Make a motion block to act as our child
        self.config_dir = tmp_dir("config_dir")

        # Store a list of our detector block views
        self.b_detectors = []

        # create a root block for the RunnableController block to reside in
        self.c = RunnableController(mri=self.main_mri, config_dir=self.config_dir.value)

        # Set up the process
        self.p.add_controller(self.c)
        self.b = self.context.block_view(self.main_mri)
        self.ss = self.c.state_set

    def tearDown(self):
        self.p.stop(timeout=1)
        shutil.rmtree(self.config_dir.value)

    def checkState(self, state):
        assert self.c.state.value == state

    def _start_process(self):
        self.checkState(self.ss.DISABLED)
        self.p.start()
        self.checkState(self.ss.READY)

    def _add_motion_block_and_part(self, mri="motion01", name="motionPart"):
        # Add block
        for c in motion_block(mri=mri, config_dir=self.config_dir.value):
            self.p.add_controller(c)
        self.b_motion = self.context.block_view(mri)
        # Add part
        self.motion_part = MisbehavingPart(mri=mri, name=name, initial_visibility=True)
        self.c.add_part(self.motion_part)

    def _add_detector_block_and_part(self, mri, name, readout_time=0.1):
        # Block
        for c in detector_block(
            mri=mri, config_dir=self.config_dir.value, readout_time=readout_time
        ):
            self.p.add_controller(c)
        # Append block view
        self.b_detectors.append(self.context.block_view(mri))
        # Part
        detector_part = DetectorChildPart(mri=mri, name=name, initial_visibility=True)
        self.c.add_part(detector_part)

    def _get_compound_generator(self, duration: float) -> CompoundGenerator:
        line1 = LineGenerator("y", "mm", 0, 2, 3)
        line2 = LineGenerator("x", "mm", 0, 2, 2)
        return CompoundGenerator([line1, line2], [], [], duration=duration)

    def _get_detector_table(
        self,
        detector_one_exposure: float,
        detector_two_exposure: Optional[float] = None,
    ) -> DetectorTable:
        if detector_two_exposure is None:
            return DetectorTable(
                [True],
                [self.detector_one_part_name],
                [self.detector_one_mri],
                [detector_one_exposure],
                [1],
            )
        else:
            return DetectorTable(
                [True, True],
                [self.detector_one_part_name, self.detector_two_part_name],
                [self.detector_one_mri, self.detector_two_mri],
                [detector_one_exposure, detector_two_exposure],
                [1, 1],
            )

    def test_validate_single_detector_calculates_correct_exposure_with_duration(self):
        # Set up a single detector
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._start_process()

        # Config
        det_one_exposure = 0.89995
        duration = 1.0
        compound_generator = self._get_compound_generator(duration)

        # Expected outputs
        expected_detectors = self._get_detector_table(det_one_exposure)

        # Validate
        actual = self.b.validate(
            generator=compound_generator, axesToMove=["x"], fileDir="/tmp"
        )

        # Check output
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_single_detector_calculates_correct_duration_with_exposure(self):
        # Set up a single detector
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._start_process()

        # Config
        det_one_exposure = 0.89995
        compound_generator = self._get_compound_generator(0.0)
        detectors = self._get_detector_table(det_one_exposure)

        # Expected outputs
        expected_duration = 1.0

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert np.isclose(actual["generator"].duration, expected_duration)
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == detectors.to_dict()

    def test_validate_single_detector_succeeds_with_both_duration_and_exposure(self):
        # Set up a single detector
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._start_process()

        # Config
        duration = 1.0
        det_one_exposure = 0.3
        compound_generator = self._get_compound_generator(duration)
        expected_detectors = self._get_detector_table(det_one_exposure)

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=expected_detectors,
        )

        # Check output
        assert actual["generator"].duration == duration
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_single_detector_sets_min_exposure_with_zero_exposure_and_duration(
        self,
    ):
        # Set up a single detector
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._start_process()

        # Config
        duration = 0.0
        det_one_exposure = 0.0
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure)

        # Expected outputs
        expected_duration = pytest.approx(0.100105)
        expected_det_one_exposure = pytest.approx(0.0001)
        expected_detectors = self._get_detector_table(expected_det_one_exposure)

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].duration == expected_duration
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_two_detectors_set_exposure_of_both_with_duration(self):
        # Set up two detectors with different readout times
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._add_detector_block_and_part(
            self.detector_two_mri, self.detector_two_part_name, readout_time=0.2
        )
        self._start_process()

        # Config
        duration = 1.0
        compound_generator = self._get_compound_generator(duration)

        # Expected outputs
        expected_det_one_exposure = 0.89995
        expected_det_two_exposure = 0.79995
        expected_detectors = self._get_detector_table(
            expected_det_one_exposure, expected_det_two_exposure
        )

        # Validate
        actual = self.b.validate(
            generator=compound_generator, axesToMove=["x"], fileDir="/tmp"
        )

        # Check output
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_two_detectors_set_exposure_of_one_with_duration_and_one_exposure(
        self,
    ):
        # Set up two detectors with different readout times
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._add_detector_block_and_part(
            self.detector_two_mri, self.detector_two_part_name, readout_time=0.2
        )
        self._start_process()

        # Config
        duration = 1.0
        det_one_exposure = 0.45
        det_two_exposure = 0.0
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure, det_two_exposure)

        # Expected outputs
        expected_det_two_exposure = 0.79995
        expected_detectors = self._get_detector_table(
            det_one_exposure, expected_det_two_exposure
        )

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

        # Validate with the detectors swapped around

        # Config
        det_one_exposure = 0.0
        det_two_exposure = 0.7
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure, det_two_exposure)

        # Expected outputs
        expected_det_one_exposure = 0.89995
        expected_detectors = self._get_detector_table(
            expected_det_one_exposure, det_two_exposure
        )

        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_two_detectors_set_duration_and_one_exposure_with_one_exposure(
        self,
    ):
        # Set up two detectors with different readout times
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._add_detector_block_and_part(
            self.detector_two_mri, self.detector_two_part_name, readout_time=0.2
        )
        self._start_process()

        # Config
        duration = 0.0
        det_one_exposure = 0.5
        det_two_exposure = 0.0
        expected_duration = 0.60003
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure, det_two_exposure)

        # Expected outputs
        expected_det_two_exposure = 0.4
        expected_detectors = self._get_detector_table(
            det_one_exposure, expected_det_two_exposure
        )

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].duration == pytest.approx(expected_duration)
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert np.allclose(actual["detectors"].to_dict()["exposure"], [0.5, 0.4])

        # Validate with the detectors swapped around
        det_one_exposure = 0.0
        det_two_exposure = 0.7
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure, det_two_exposure)

        # Expected ouputs
        expected_duration = 0.900045
        expected_det_one_exposure = pytest.approx(0.8)
        expected_det_two_exposure = pytest.approx(0.7)
        expected_detectors = self._get_detector_table(
            expected_det_one_exposure, expected_det_two_exposure
        )

        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].duration == pytest.approx(
            expected_duration, rel=1e-6
        )
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_two_detectors_set_duration_with_both_exposures(self):
        # Set up two detectors with different readout times
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._add_detector_block_and_part(
            self.detector_two_mri, self.detector_two_part_name, readout_time=0.2
        )
        self._start_process()

        # Config
        duration = 0.0
        det_one_exposure = 0.3
        det_two_exposure = 0.5
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure, det_two_exposure)

        # Expected outputs
        expected_duration = 0.700035
        expected_det_one_exposure = pytest.approx(det_one_exposure)
        expected_det_two_exposure = pytest.approx(det_two_exposure)
        expected_detectors = self._get_detector_table(
            expected_det_one_exposure, expected_det_two_exposure
        )

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].duration == pytest.approx(
            expected_duration, rel=1e-6
        )
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_two_detectors_calculates_min_duration_for_no_duration_or_exposure(
        self,
    ):
        # Set up two detectors with different readout times
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._add_detector_block_and_part(
            self.detector_two_mri, self.detector_two_part_name, readout_time=0.3
        )
        self._start_process()

        # Config
        duration = 0.0
        det_one_exposure = 0.0
        det_two_exposure = 0.0
        compound_generator = self._get_compound_generator(duration)
        detectors = self._get_detector_table(det_one_exposure, det_two_exposure)

        # Expected outputs
        expected_duration = pytest.approx(0.300115)
        expected_det_one_exposure = pytest.approx(0.2001)
        expected_det_two_exposure = pytest.approx(0.0001)
        expected_detectors = self._get_detector_table(
            expected_det_one_exposure, expected_det_two_exposure
        )

        # Validate
        actual = self.b.validate(
            generator=compound_generator,
            axesToMove=["x"],
            fileDir="/tmp",
            detectors=detectors,
        )

        # Check output
        assert actual["generator"].duration == expected_duration
        actual["generator"].duration = 0.0
        assert actual["generator"].to_dict() == compound_generator.to_dict()
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_detectors.to_dict()

    def test_validate_with_line_generator_increases_duration_for_motion_part(self):
        # Setup two detectors and our motion block
        self._add_motion_block_and_part()
        self._add_detector_block_and_part(
            self.detector_one_mri, self.detector_one_part_name
        )
        self._add_detector_block_and_part(
            self.detector_two_mri, self.detector_two_part_name, readout_time=0.25
        )
        self._start_process()

        # Config
        compound_generator = self._get_compound_generator(0.1)

        # Expected outputs
        expected_duration = 0.5
        expected_det_one_exposure = 0.399975
        expected_det_two_exposure = 0.249975
        expected_table = self._get_detector_table(
            expected_det_one_exposure, expected_det_two_exposure
        )

        # Call validate
        actual = self.b.validate(
            generator=compound_generator, axesToMove=["x"], fileDir="/tmp"
        )

        # Check output
        assert actual["generator"].duration == expected_duration
        assert actual["axesToMove"] == ["x"]
        assert actual["detectors"].to_dict() == expected_table.to_dict()
        actual["generator"].duration = 0.1
        assert actual["generator"].to_dict() == compound_generator.to_dict()
