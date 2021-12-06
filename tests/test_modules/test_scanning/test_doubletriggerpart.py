from mock import MagicMock, call

from malcolm.core import Context, Process
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.scanning.blocks import double_trigger_block
from malcolm.modules.scanning.hooks import ReportStatusHook, ValidateHook
from malcolm.modules.scanning.infos import DetectorMutiframeInfo
from malcolm.modules.scanning.parts import DoubleTriggerPart
from malcolm.modules.scanning.util import DetectorTable
from malcolm.testutil import ChildTestCase


def get_detector_table(detector_mri, frames_per_step, enabled=True):
    return DetectorTable(
        [enabled, True],
        ["detector", "panda"],
        [detector_mri, "ML-PANDA-01"],
        [1.0, 0.0],
        [frames_per_step, 1],
    )


class TestDoubleTriggerPart(ChildTestCase):
    def setUp(self):
        self.process = Process()
        self.context = Context(self.process)

        self.detector_mri = "ML-DET-01"
        self.block_mri = "ML-MULTI-01"

        # Create a detector to which this part communicates
        self.detector = ManagerController(self.detector_mri, "/tmp", use_git=False)

        # Create a block for this part
        self.child = self.create_child_block(
            double_trigger_block,
            self.process,
            mri=self.block_mri,
            detector=self.detector_mri,
        )

        self.double_trigger_part = DoubleTriggerPart(
            name="detectorDoubleTriggers", mri=self.block_mri
        )

    def test_setup_has_required_hooks(self):
        mock_registrar = MagicMock(name="registrar_mock")

        self.double_trigger_part.setup(mock_registrar)

        mock_registrar.hook.assert_has_calls(
            [
                call(ReportStatusHook, self.double_trigger_part.on_report_status),
                call(ValidateHook, self.double_trigger_part.on_validate),
            ]
        )

    def test_on_report_status_reports_DetectorMultiframeInfo(self):
        info = self.double_trigger_part.on_report_status(self.context)

        assert info.mri == self.detector_mri
        assert isinstance(info, DetectorMutiframeInfo)

    def test_on_validate_succeeds_when_detector_is_disabled(self):
        detectors = get_detector_table(self.detector_mri, 0, enabled=False)

        self.double_trigger_part.on_validate(self.context, detectors=detectors)

    def test_on_validate_succeeds(self):
        detectors = get_detector_table(self.detector_mri, 2)

        self.double_trigger_part.on_validate(self.context, detectors=detectors)

    def test_on_validate_raises_ValueError_for_bad_frames_per_step(self):
        detectors_negative_frames = get_detector_table(self.detector_mri, -1)
        detectors_zero_frames = get_detector_table(self.detector_mri, 0)

        self.assertRaises(
            ValueError,
            self.double_trigger_part.on_validate,
            self.context,
            detectors=detectors_negative_frames,
        )

        self.assertRaises(
            ValueError,
            self.double_trigger_part.on_validate,
            self.context,
            detectors=detectors_zero_frames,
        )

    def test_on_validate_raises_AssertionError_without_detector_table(
        self,
    ):
        self.assertRaises(
            AssertionError, self.double_trigger_part.on_validate, self.context
        )
