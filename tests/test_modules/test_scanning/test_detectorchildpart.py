import os
import shutil
import tempfile
import unittest
from typing import List, Union
from unittest.mock import Mock, patch

from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator, ConcatGenerator, LineGenerator

from malcolm.core import (
    AMri,
    APartName,
    BadValueError,
    Context,
    NumberMeta,
    Part,
    PartRegistrar,
    Process,
)
from malcolm.modules.builtin.hooks import AContext, InitHook, ResetHook
from malcolm.modules.builtin.util import LayoutTable, set_tags
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.hooks import (
    AFileDir,
    AFileTemplate,
    AFormatName,
    ConfigureHook,
    ReportStatusHook,
    RunHook,
)
from malcolm.modules.scanning.infos import DetectorMutiframeInfo
from malcolm.modules.scanning.parts import (
    DatasetTablePart,
    DetectorChildPart,
    ExposureDeadtimePart,
)
from malcolm.modules.scanning.util import DetectorTable, RunnableStates

with Anno("How long to wait"):
    AWait = float


class MockChildState:
    """Mock child state by iterating through a list of values"""

    def __init__(self, values: Union[RunnableStates, List[RunnableStates]]):
        self.values = values
        self.index = 0

    def __getattr__(self, attr):
        if attr == "value":
            if isinstance(self.values, List):
                self.index += 1
                return self.values[self.index - 1]
            else:
                return self.values
        raise AttributeError(
            f"{self.__class__.__name__} object has no attribute {attr}"
        )


class WaitingPart(Part):
    def __init__(self, name: APartName, wait: AWait = 0.0) -> None:
        super(WaitingPart, self).__init__(name)
        meta = NumberMeta("float64", "How long to wait")
        set_tags(meta, writeable=True)
        self.attr = meta.create_attribute_model(wait)
        self.register_hooked(RunHook, self.run)
        self.register_hooked(ConfigureHook, self.configure)

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.add_attribute_model(self.name, self.attr, self.attr.set_value)
        # Tell the controller to expose some extra configure parameters
        registrar.report(ConfigureHook.create_info(self.configure))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(
        self,
        fileDir: AFileDir,
        formatName: AFormatName = "det",
        fileTemplate: AFileTemplate = "%s.h5",
    ) -> None:
        # Don't do anything, just take the args so we look like a detector
        pass

    @add_call_types
    def run(self, context: AContext) -> None:
        context.sleep(self.attr.value)


class MaybeMultiPart(Part):
    def __init__(self, mri: AMri) -> None:
        super(MaybeMultiPart, self).__init__("MULTI" + mri)
        self.mri = mri
        self.active = False

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.hook(ReportStatusHook, self.on_report_status)

    @add_call_types
    def on_report_status(self):
        if self.active:
            return DetectorMutiframeInfo(self.mri)


DESIGN_PATH = os.path.join(os.path.dirname(__file__), "designs")


class FaultyPart(Part):
    def setup(self, registrar: PartRegistrar) -> None:
        registrar.hook((InitHook, ResetHook), self.fail)

    def fail(self):
        raise ValueError("I'm bad")


class TestDetectorChildPartMethods(unittest.TestCase):
    def setUp(self):
        self.detector_part = DetectorChildPart(
            name="CHILDPART", mri="child", initial_visibility=True
        )

    @patch("malcolm.modules.builtin.parts.ChildPart.on_init")
    def test_part_does_not_become_faulty_with_value_on_init(self, mock_on_init):
        mock_context = Mock(name="context_mock")

        self.detector_part.on_init(mock_context)

        mock_on_init.assert_called_once_with(mock_context)
        self.assertEqual(False, self.detector_part.faulty)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_init")
    def test_part_becomes_faulty_with_BadValueError_on_init(self, mock_on_init):
        mock_context = Mock(name="context_mock")
        mock_on_init.side_effect = BadValueError()

        self.detector_part.on_init(mock_context)

        mock_on_init.assert_called_once_with(mock_context)
        self.assertEqual(True, self.detector_part.faulty)

    def test_on_run_has_future_when_child_is_armed(self):
        mock_context = Mock(name="context_mock")
        mock_child = Mock(name="child_mock")
        mock_child.state.value = RunnableStates.ARMED
        mock_child.run_async.return_value = "run_async_return_value"
        mock_child.when_value_matches_async.return_value = (
            "when_value_matches_return_value"
        )
        mock_context.block_view.return_value = mock_child

        self.detector_part.on_run(mock_context)

        assert self.detector_part.run_future == "run_async_return_value"
        mock_context.wait_all_futures.assert_called_once_with(
            "when_value_matches_return_value"
        )

    def test_on_run_resumes_when_child_is_not_armed(self):
        mock_context = Mock(name="context_mock")
        mock_child = Mock(name="child_mock")
        mock_child.state.value = RunnableStates.PAUSED
        mock_child.when_value_matches_async.return_value = (
            "when_value_matches_return_value"
        )
        mock_context.block_view.return_value = mock_child

        self.detector_part.on_run(mock_context)

        mock_child.resume.assert_called_once()
        mock_context.wait_all_futures.assert_called_once_with(
            "when_value_matches_return_value"
        )

    def test_on_run_raises_run_future_exception_when_child_is_in_fault(self):
        mock_context = Mock(name="context_mock")
        mock_child = Mock(name="child_mock")
        mock_run_future = Mock(name="run_future_mock")
        mock_run_future.exception.return_value = TimeoutError()
        mock_child.state = MockChildState([RunnableStates.ARMED, RunnableStates.FAULT])
        mock_child.run_async.return_value = mock_run_future
        mock_context.block_view.return_value = mock_child
        mock_context.wait_all_futures.side_effect = BadValueError()

        self.assertRaises(TimeoutError, self.detector_part.on_run, mock_context)

    def test_on_run_re_raises_BadValueError_when_child_is_not_in_fault(self):
        mock_context = Mock(name="context_mock")
        mock_child = Mock(name="child_mock")
        mock_child.state = MockChildState(RunnableStates.ARMED)
        mock_context.block_view.return_value = mock_child
        mock_context.wait_all_futures.side_effect = BadValueError

        self.assertRaises(BadValueError, self.detector_part.on_run, mock_context)


class TestDetectorChildPart(unittest.TestCase):
    def setUp(self):
        self.p = Process("process1")
        self.context = Context(self.p)

        # Make a fast child, this will load the wait of 0.01 from saved file
        c1 = RunnableController(
            mri="fast", config_dir=DESIGN_PATH, use_git=False, initial_design="fast"
        )
        c1.add_part(WaitingPart("wait"))
        c1.add_part(ExposureDeadtimePart("dt", 0.001))
        c1.add_part(DatasetTablePart("dset"))
        self.p.add_controller(c1)

        # And a slow one, this has the same saved files as fast, but doesn't
        # load at startup
        c2 = RunnableController(mri="slow", config_dir=DESIGN_PATH, use_git=False)
        c2.add_part(WaitingPart("wait", 0.123))
        c2.add_part(DatasetTablePart("dset"))
        self.p.add_controller(c2)

        # And a faulty one, this is hidden at startup by default
        c3 = RunnableController(mri="faulty", config_dir=DESIGN_PATH, use_git=False)
        c3.add_part(FaultyPart("bad"))
        c3.add_part(DatasetTablePart("dset"))
        self.p.add_controller(c3)

        # And a top level one, this loads slow and fast designs for the
        # children on every configure (or load), but not at init
        self.ct = RunnableController(
            mri="top", config_dir=DESIGN_PATH, use_git=False, initial_design="default"
        )
        self.ct.add_part(
            DetectorChildPart(name="FAST", mri="fast", initial_visibility=True)
        )
        self.ct.add_part(
            DetectorChildPart(name="SLOW", mri="slow", initial_visibility=True)
        )
        self.ct.add_part(
            DetectorChildPart(name="BAD", mri="faulty", initial_visibility=False)
        )
        self.ct.add_part(
            DetectorChildPart(
                name="BAD2",
                mri="faulty",
                initial_visibility=False,
                initial_frames_per_step=0,
            )
        )
        self.fast_multi = MaybeMultiPart("fast")
        self.slow_multi = MaybeMultiPart("slow")
        self.ct.add_part(self.fast_multi)
        self.ct.add_part(self.slow_multi)
        self.p.add_controller(self.ct)

        # Some blocks to interface to them
        self.b = self.context.block_view("top")
        self.bf = self.context.block_view("fast")
        self.bs = self.context.block_view("slow")

        # start the process off
        self.p.start()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self.p.stop(timeout=1)
        shutil.rmtree(self.tmpdir)

    def make_generator(self):
        line1 = LineGenerator("y", "mm", 0, 2, 3)
        line2 = LineGenerator("x", "mm", 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration=1)
        return compound

    def test_init(self):
        assert list(self.b.configure.meta.defaults["detectors"].rows()) == [
            [True, "FAST", "fast", 0.0, 1],
            [True, "SLOW", "slow", 0.0, 1],
        ]

    def test_validate_returns_exposures(self):
        ret = self.b.validate(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows(
                [(True, "SLOW", "slow", 0.0, 1), (True, "FAST", "fast", 0.0, 1)]
            ),
        )
        assert list(ret.detectors.rows()) == [
            [True, "SLOW", "slow", 0.0, 1],
            [True, "FAST", "fast", 0.99895, 1],
        ]

    def test_guessing_frames_1(self):
        ret = self.b.validate(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows(
                [(True, "FAST", "fast", 0.5, 0), (True, "SLOW", "slow", 0.0, 1)]
            ),
        )
        assert list(ret.detectors.rows()) == [
            [True, "FAST", "fast", 0.5, 1],
            [True, "SLOW", "slow", 0.0, 1],
        ]

    def test_setting_exposure_on_no_exposure_det_fails(self):
        with self.assertRaises(BadValueError) as cm:
            self.b.validate(
                self.make_generator(),
                self.tmpdir,
                detectors=DetectorTable.from_rows(
                    [(True, "FAST", "fast", 0.0, 1), (True, "SLOW", "slow", 0.5, 1)]
                ),
            )
        assert str(cm.exception) == "Detector SLOW doesn't take exposure"

    def test_guessing_frames_and_exposure(self):
        self.slow_multi.active = True
        ret = self.b.validate(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows([(True, "FAST", "fast", 0.0, 0)]),
        )
        assert list(ret.detectors.rows()) == [
            [True, "FAST", "fast", 0.99895, 1],
            [False, "SLOW", "slow", 0, 0],
        ]

    def test_guessing_frames_5(self):
        self.fast_multi.active = True
        ret = self.b.validate(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows(
                [(True, "FAST", "fast", 0.198, 0), (True, "SLOW", "slow", 0.0, 1)]
            ),
        )
        assert list(ret.detectors.rows()) == [
            [True, "FAST", "fast", 0.198, 5],
            [True, "SLOW", "slow", 0.0, 1],
        ]

    def test_adding_faulty_fails(self):
        t = LayoutTable.from_rows([["BAD", "faulty", 0, 0, True]])
        self.b.layout.put_value(t)
        assert list(self.b.configure.meta.defaults["detectors"].rows()) == [
            [True, "FAST", "fast", 0.0, 1],
            [True, "SLOW", "slow", 0.0, 1],
            [True, "BAD", "faulty", 0.0, 1],
        ]
        with self.assertRaises(BadValueError) as cm:
            self.b.configure(self.make_generator(), self.tmpdir)
        assert str(cm.exception) == (
            "Detector BAD was faulty at init and is unusable. "
            "If the detector is now working please restart Malcolm"
        )
        self.b.configure(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows([(False, "BAD", "faulty", 0.0, 1)]),
        )
        self.b.reset()
        t = LayoutTable.from_rows([["BAD", "faulty", 0, 0, False]])
        self.b.layout.put_value(t)
        self.test_init()
        self.b.configure(self.make_generator(), self.tmpdir)

    def test_adding_faulty_non_default_works(self):
        t = LayoutTable.from_rows([["BAD2", "faulty", 0, 0, True]])
        self.b.layout.put_value(t)
        assert list(self.b.configure.meta.defaults["detectors"].rows()) == [
            [True, "FAST", "fast", 0.0, 1],
            [True, "SLOW", "slow", 0.0, 1],
            [False, "BAD2", "faulty", 0.0, 1],
        ]
        self.b.configure(self.make_generator(), self.tmpdir)

    def test_only_one_det(self):
        # Disable one detector
        self.b.configure(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows(
                [(False, "SLOW", "slow", 0.0, 0), [True, "FAST", "fast", 0.0, 1]]
            ),
        )
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Armed"
        self.b.completedSteps.put_value(2)
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Armed"
        self.b.run()
        assert self.b.state.value == "Finished"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Finished"
        self.b.reset()
        assert self.b.state.value == "Ready"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Ready"
        self.b.abort()
        assert self.b.state.value == "Aborted"
        assert self.bs.state.value == "Aborted"
        assert self.bf.state.value == "Aborted"

    def test_multi_frame_no_infos_fails(self):
        with self.assertRaises(BadValueError) as cm:
            self.b.configure(
                self.make_generator(),
                self.tmpdir,
                detectors=DetectorTable.from_rows(
                    [(True, "SLOW", "slow", 0.0, 1), (True, "FAST", "fast", 0.0, 5)]
                ),
            )
        assert str(cm.exception) == (
            "There are no trigger multipliers setup for Detector 'FAST' "
            "so framesPerStep can only be 0 or 1 for this row in the detectors "
            "table"
        )

    def test_multi_frame_fast_det(self):
        self.fast_multi.active = True
        self.b.configure(
            self.make_generator(),
            self.tmpdir,
            detectors=DetectorTable.from_rows(
                [(True, "SLOW", "slow", 0.0, 1), (True, "FAST", "fast", 0.0, 5)]
            ),
        )
        assert self.b.completedSteps.value == 0
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 6
        assert self.bs.completedSteps.value == 0
        assert self.bs.totalSteps.value == 6
        assert self.bs.configuredSteps.value == 6
        assert self.bf.completedSteps.value == 0
        assert self.bf.totalSteps.value == 30
        assert self.bf.configuredSteps.value == 30

    def test_bad_det_mri(self):
        # Send mismatching rows
        with self.assertRaises(AssertionError) as cm:
            self.b.configure(
                self.make_generator(),
                self.tmpdir,
                axesToMove=(),
                detectors=DetectorTable.from_rows([(True, "SLOW", "fast", 0.0, 0)]),
            )
        assert str(cm.exception) == "SLOW has mri slow, passed fast"

    def test_not_paused_when_resume(self):
        # Set it up to do 6 steps
        self.b.configure(
            self.make_generator(),
            self.tmpdir,
            axesToMove=(),
            detectors=DetectorTable.from_rows(
                [(True, "FAST", "fast", 0, 1), (True, "SLOW", "slow", 0, 1)]
            ),
        )
        assert self.b.completedSteps.value == 0
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 1
        # Do one step
        self.b.run()
        assert self.b.completedSteps.value == 1
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 2
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Armed"
        assert self.bf.state.value == "Armed"
        # Now do a second step but pause before the second one is done
        f = self.b.run_async()
        self.context.sleep(0.2)
        assert self.b.state.value == "Running"
        assert self.bf.state.value == "Armed"
        assert self.bs.state.value == "Running"
        self.b.pause()
        assert self.b.state.value == "Paused"
        assert self.bf.state.value == "Armed"
        assert self.bs.state.value == "Paused"
        assert self.b.completedSteps.value == 1
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 2
        self.b.resume()
        self.context.wait_all_futures(f)
        assert self.b.completedSteps.value == 2
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 3

    def test_parent_with_initial_config_does_not_set_child(self):
        assert self.bs.wait.value == 0.123
        assert self.bs.design.value == ""
        assert self.bf.wait.value == 0.01
        assert self.bf.design.value == "fast"
        assert self.b.design.value == "default"
        assert self.b.modified.value is True
        assert self.b.modified.alarm.message == "SLOW.design.value = '' not 'slow'"
        self.b.configure(self.make_generator(), self.tmpdir, axesToMove=())
        assert self.bs.wait.value == 1.0
        assert self.bs.design.value == "slow"
        assert self.bf.wait.value == 0.01
        assert self.bf.design.value == "fast"
        assert self.b.design.value == "default"
        assert self.b.modified.value is False

    def make_generator_breakpoints(self):
        line1 = LineGenerator("x", "mm", -10, -10, 5)
        line2 = LineGenerator("x", "mm", 0, 180, 10)
        line3 = LineGenerator("x", "mm", 190, 190, 2)
        duration = 0.01
        concat = ConcatGenerator([line1, line2, line3])

        return CompoundGenerator([concat], [], [], duration)

    def checkSteps(self, block, configured, completed, total):
        assert block.configuredSteps.value == configured
        assert block.completedSteps.value == completed
        assert block.totalSteps.value == total

    def checkState(self, block, state):
        assert block.state.value == state

    def test_breakpoints_tomo(self):
        breakpoints = [2, 3, 10, 2]
        # Configure RunnableController(mri='top')
        self.b.configure(
            generator=self.make_generator_breakpoints(),
            fileDir=self.tmpdir,
            detectors=DetectorTable.from_rows(
                [[False, "SLOW", "slow", 0.0, 1], [True, "FAST", "fast", 0.0, 1]]
            ),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

        assert self.ct.configure_params.generator.size == 17
        self.checkSteps(self.b, 2, 0, 17)
        self.checkSteps(self.bf, 2, 0, 17)
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Armed"

        self.b.run()
        self.checkSteps(self.b, 5, 2, 17)
        self.checkSteps(self.bf, 5, 2, 17)
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Armed"

        self.b.run()
        self.checkSteps(self.b, 15, 5, 17)
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Armed"

        self.b.run()
        self.checkSteps(self.b, 17, 15, 17)
        assert self.b.state.value == "Armed"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Armed"

        self.b.run()
        self.checkSteps(self.b, 17, 17, 17)
        self.checkSteps(self.bf, 17, 17, 17)
        assert self.b.state.value == "Finished"
        assert self.bs.state.value == "Ready"
        assert self.bf.state.value == "Finished"

    def test_breakpoints_with_pause(self):
        breakpoints = [2, 3, 10, 2]
        self.b.configure(
            generator=self.make_generator_breakpoints(),
            fileDir=self.tmpdir,
            detectors=DetectorTable.from_rows(
                [[False, "SLOW", "slow", 0.0, 1], [True, "FAST", "fast", 0.0, 1]]
            ),
            axesToMove=["x"],
            breakpoints=breakpoints,
        )

        assert self.ct.configure_params.generator.size == 17

        self.checkSteps(self.b, 2, 0, 17)
        self.checkSteps(self.bf, 2, 0, 17)
        self.checkState(self.b, RunnableStates.ARMED)

        self.b.run()
        self.checkSteps(self.b, 5, 2, 17)
        self.checkSteps(self.bf, 5, 2, 17)
        self.checkState(self.b, RunnableStates.ARMED)

        # rewind
        self.b.pause(lastGoodStep=1)
        self.checkSteps(self.b, 2, 1, 17)
        self.checkSteps(self.bf, 2, 1, 17)
        self.checkState(self.b, RunnableStates.ARMED)
        self.b.run()
        self.checkSteps(self.b, 5, 2, 17)
        self.checkSteps(self.bf, 5, 2, 17)
        self.checkState(self.b, RunnableStates.ARMED)

        self.b.run()
        self.checkSteps(self.b, 15, 5, 17)
        self.checkSteps(self.bf, 15, 5, 17)
        self.checkState(self.b, RunnableStates.ARMED)

        self.b.run()
        self.checkSteps(self.b, 17, 15, 17)
        self.checkSteps(self.bf, 17, 15, 17)
        self.checkState(self.b, RunnableStates.ARMED)

        # rewind
        self.b.pause(lastGoodStep=11)
        self.checkSteps(self.b, 15, 11, 17)
        self.checkSteps(self.bf, 15, 11, 17)
        self.checkState(self.b, RunnableStates.ARMED)
        self.b.run()
        self.checkSteps(self.b, 17, 15, 17)
        self.checkSteps(self.bf, 17, 15, 17)
        self.checkState(self.b, RunnableStates.ARMED)

        self.b.run()
        self.checkSteps(self.b, 17, 17, 17)
        self.checkSteps(self.bf, 17, 17, 17)
        self.checkState(self.b, RunnableStates.FINISHED)
