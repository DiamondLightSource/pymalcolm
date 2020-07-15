import os
import shutil
import tempfile
import unittest

from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator, LineGenerator

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
from malcolm.modules.scanning.util import DetectorTable

with Anno("How long to wait"):
    AWait = float


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
        ct = RunnableController(
            mri="top", config_dir=DESIGN_PATH, use_git=False, initial_design="default"
        )
        ct.add_part(DetectorChildPart(name="FAST", mri="fast", initial_visibility=True))
        ct.add_part(DetectorChildPart(name="SLOW", mri="slow", initial_visibility=True))
        ct.add_part(
            DetectorChildPart(name="BAD", mri="faulty", initial_visibility=False)
        )
        ct.add_part(
            DetectorChildPart(
                name="BAD2",
                mri="faulty",
                initial_visibility=False,
                initial_frames_per_step=0,
            )
        )
        self.fast_multi = MaybeMultiPart("fast")
        self.slow_multi = MaybeMultiPart("slow")
        ct.add_part(self.fast_multi)
        ct.add_part(self.slow_multi)
        self.p.add_controller(ct)

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
