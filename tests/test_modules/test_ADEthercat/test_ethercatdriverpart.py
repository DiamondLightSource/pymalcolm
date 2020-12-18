from mock import Mock, call, patch
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADEthercat.blocks import ethercat_driver_block
from malcolm.modules.ADEthercat.parts import EthercatDriverPart
from malcolm.modules.scanning.hooks import (
    PostRunArmedHook,
    PostRunReadyHook,
    PreRunHook,
)
from malcolm.testutil import ChildTestCase


class TestEthercatDriverPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.mri = "mri"
        self.child = self.create_child_block(
            ethercat_driver_block, self.process, mri=self.mri, prefix="prefix"
        )
        self.mock_when_value_matches(self.child)
        # readoutTime used to be 0.002, not any more...
        self.ethercat_driver_part = EthercatDriverPart(name="m", mri="mri")
        self.context.set_notify_dispatch_request(
            self.ethercat_driver_part.notify_dispatch_request
        )
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def _do_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 200, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 10)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 2000
        file_dir = "/tmp"
        self.ethercat_driver_part.on_configure(
            self.context,
            completed_steps,
            steps_to_do,
            {},
            generator=generator,
            fileDir=file_dir,
        )

    def test_constructor(self):
        # Constructor already called, ensure soft trigger mode is set
        self.assertEqual(self.ethercat_driver_part.soft_trigger_modes, "Internal")

    def test_configure(self):
        # We wait to be armed, so set this here
        # self.set_attributes(self.child, acquiring=True)
        self._do_configure()
        assert self.child.handled_requests.mock_calls == [
            call.put("arrayCallbacks", True),
            call.put("arrayCounter", 0),
            call.put("imageMode", "Multiple"),
            call.put("numImages", 2000),
            # Custom setup method now takes over
            call.put("imageMode", "Continuous"),
            call.put("triggerMode", "Internal"),
            call.put("numberOfSamples", 1000),
        ]

    def test_start_acquisition(self):
        # Just check we call the arm_detector method
        mock_arm_detector = Mock(name="mock_arm_detector_method")
        self.ethercat_driver_part.arm_detector = mock_arm_detector
        self.ethercat_driver_part.start_acquisition(self.context)

        mock_arm_detector.assert_called_once_with(self.context)

    # Patch the super setup() method so we only get desired calls
    @patch("malcolm.modules.ADCore.parts.DetectorDriverPart.setup")
    def test_setup(self, mocked_super_setup):
        # Check we hook on PreRun to arm and PostRunReady to abort
        mock_registrar = Mock(name="mock_registrar")
        self.ethercat_driver_part.setup(mock_registrar)

        assert mock_registrar.hook.mock_calls == [
            call(PreRunHook, self.ethercat_driver_part.start_acquisition),
            call(
                (PostRunArmedHook, PostRunReadyHook), self.ethercat_driver_part.on_abort
            ),
        ]

    def test_on_run(self):
        # on_run does nothing, just call and ensure no exception is raised
        self.ethercat_driver_part.on_run(self.context)
