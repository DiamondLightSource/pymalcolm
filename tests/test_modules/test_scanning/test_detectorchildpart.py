import shutil
import tempfile
import unittest
import os

from annotypes import add_call_types, Anno
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Part, Process, Context, APartName, PartRegistrar, \
    NumberMeta, AMri, BadValueError
from malcolm.modules.builtin.hooks import AContext
from malcolm.modules.builtin.util import set_tags
from malcolm.modules.scanning.infos import DetectorMutiframeInfo
from malcolm.modules.scanning.parts import DetectorChildPart, DatasetTablePart, \
    ExposureDeadtimePart
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.hooks import AFileDir, AFormatName, \
    AFileTemplate, RunHook, ConfigureHook, ReportStatusHook
from malcolm.modules.scanning.util import DetectorTable

with Anno("How long to wait"):
    AWait = float


class WaitingPart(Part):
    def __init__(self, name, wait=0.0):
        # type: (APartName, AWait) -> None
        super(WaitingPart, self).__init__(name)
        meta = NumberMeta("float64", "How long to wait")
        set_tags(meta, writeable=True)
        self.attr = meta.create_attribute_model(wait)
        self.register_hooked(RunHook, self.run)
        self.register_hooked(ConfigureHook, self.configure)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.attr.set_value)
        # Tell the controller to expose some extra configure parameters
        registrar.report(ConfigureHook.create_info(self.configure))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  fileDir,  # type: AFileDir
                  formatName="det",  # type: AFormatName
                  fileTemplate="%s.h5",  # type: AFileTemplate
                  ):
        # type: (...) -> None
        # Don't do anything, just take the args so we look like a detector
        pass

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        context.sleep(self.attr.value)


class MaybeMultiPart(Part):
    def __init__(self, mri):
        # type: (AMri) -> None
        super(MaybeMultiPart, self).__init__("MULTI" + mri)
        self.mri = mri
        self.active = False

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.hook(ReportStatusHook, self.report_status)

    @add_call_types
    def report_status(self):
        if self.active:
            return DetectorMutiframeInfo(self.mri)


DESIGN_PATH = os.path.join(os.path.dirname(__file__), "designs")


class TestDetectorChildPart(unittest.TestCase):

    def setUp(self):
        self.p = Process('process1')
        self.context = Context(self.p)

        # Make a fast child, this will load the wait of 0.01 from saved file
        c1 = RunnableController(
            mri="fast", config_dir=DESIGN_PATH, use_git=False,
            initial_design="fast")
        c1.add_part(WaitingPart("wait"))
        c1.add_part(ExposureDeadtimePart("dt", 0.001))
        c1.add_part(DatasetTablePart("dset"))
        self.p.add_controller(c1)

        # And a slow one, this has the same saved files as fast, but doesn't
        # load at startup
        c2 = RunnableController(
            mri="slow", config_dir=DESIGN_PATH, use_git=False)
        c2.add_part(WaitingPart("wait", 0.123))
        c2.add_part(DatasetTablePart("dset"))
        self.p.add_controller(c2)

        # And a top level one, this loads slow and fast designs for the
        # children on every configure (or load), but not at init
        c3 = RunnableController(
            mri="top", config_dir=DESIGN_PATH, use_git=False,
            initial_design="default"
        )
        c3.add_part(
            DetectorChildPart(name="FAST", mri="fast", initial_visibility=True))
        c3.add_part(
            DetectorChildPart(name="SLOW", mri="slow", initial_visibility=True))
        self.fast_multi = MaybeMultiPart("fast")
        self.slow_multi = MaybeMultiPart("slow")
        c3.add_part(self.fast_multi)
        c3.add_part(self.slow_multi)
        self.p.add_controller(c3)

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
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration=1)
        return compound

    def test_init(self):
        assert list(self.b.configure.meta.defaults["detectors"].rows()) == [
            [True, "FAST", "fast", 0.0, 1],
            [True, "SLOW", "slow", 0.0, 1]
        ]

    def test_validate_returns_exposures(self):
        ret = self.b.validate(
            self.make_generator(), self.tmpdir,
            detectors=DetectorTable.from_rows([
                (True, "SLOW", "slow", 0.0, 1),
                (True, "FAST", "fast", 0.0, 1)
            ])
        )
        assert list(ret.detectors.rows()) == [
            [True, 'SLOW', 'slow', 0.0, 1],
            [True, 'FAST', 'fast', 0.99895, 1],
        ]

    def test_guessing_frames_1(self):
        ret = self.b.validate(
            self.make_generator(), self.tmpdir,
            detectors=DetectorTable.from_rows([
                (True, "FAST", "fast", 0.5, 0),
                (True, "SLOW", "slow", 0.0, 1),
            ])
        )
        assert list(ret.detectors.rows()) == [
            [True, 'FAST', 'fast', 0.5, 1],
            [True, 'SLOW', 'slow', 0.0, 1]
        ]

    def test_setting_exposure_on_no_exposure_det_fails(self):
        with self.assertRaises(BadValueError) as cm:
            self.b.validate(
                self.make_generator(), self.tmpdir,
                detectors=DetectorTable.from_rows([
                    (True, "FAST", "fast", 0.0, 1),
                    (True, "SLOW", "slow", 0.5, 1),
                ])
            )
        assert str(cm.exception) == "Detector SLOW doesn't take exposure"

    def test_guessing_frames_and_exposure(self):
        self.slow_multi.active = True
        ret = self.b.validate(
            self.make_generator(), self.tmpdir,
            detectors=DetectorTable.from_rows([
                (True, "FAST", "fast", 0.0, 0),
            ])
        )
        assert list(ret.detectors.rows()) == [
            [True, 'FAST', 'fast', 0.99895, 1],
            [False, 'SLOW', 'slow', 0, 0]
        ]

    def test_guessing_frames_5(self):
        self.fast_multi.active = True
        ret = self.b.validate(
            self.make_generator(), self.tmpdir,
            detectors=DetectorTable.from_rows([
                (True, "FAST", "fast", 0.198, 0),
                (True, "SLOW", "slow", 0.0, 1),
            ])
        )
        assert list(ret.detectors.rows()) == [
            [True, 'FAST', 'fast', 0.198, 5],
            [True, 'SLOW', 'slow', 0.0, 1]
        ]

    def test_only_one_det(self):
        # Disable one detector
        self.b.configure(
            self.make_generator(), self.tmpdir,
            detectors=DetectorTable.from_rows([
                (False, "SLOW", "slow", 0.0, 0),
                [True, 'FAST', 'fast', 0.0, 1],
            ])
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
                self.make_generator(), self.tmpdir,
                detectors=DetectorTable.from_rows([
                    (True, "SLOW", "slow", 0.0, 1),
                    (True, "FAST", "fast", 0.0, 5)
                ])
            )
        assert str(cm.exception) == "There are no trigger multipliers setup for Detector 'FAST' so framesPerStep can only be 0 or 1 for this row in the detectors table"

    def test_multi_frame_fast_det(self):
        self.fast_multi.active = True
        self.b.configure(
            self.make_generator(), self.tmpdir,
            detectors=DetectorTable.from_rows([
                (True, "SLOW", "slow", 0.0, 1),
                (True, "FAST", "fast", 0.0, 5)
            ])
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
                self.make_generator(), self.tmpdir, axesToMove=(),
                detectors=DetectorTable.from_rows([
                    (True, "SLOW", "fast", 0.0, 0)
                ])
            )
        assert str(cm.exception) == 'SLOW has mri slow, passed fast'

    def test_not_paused_when_resume(self):
        # Set it up to do 6 steps
        self.b.configure(
            self.make_generator(), self.tmpdir, axesToMove=(),
            detectors=DetectorTable.from_rows([
                (True, "FAST", "fast", 0, 1),
                (True, "SLOW", "slow", 0, 1)
            ])
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
        assert self.b.modified.alarm.message == \
            "SLOW.design.value = '' not 'slow'"
        self.b.configure(self.make_generator(), self.tmpdir, axesToMove=())
        assert self.bs.wait.value == 1.0
        assert self.bs.design.value == "slow"
        assert self.bf.wait.value == 0.01
        assert self.bf.design.value == "fast"
        assert self.b.design.value == "default"
        assert self.b.modified.value is False
