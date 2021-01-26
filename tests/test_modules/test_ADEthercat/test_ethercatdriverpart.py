from mock import Mock, call, patch
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADEthercat.blocks import ethercat_driver_block
from malcolm.modules.ADEthercat.parts import EthercatDriverPart
from malcolm.modules.scanning.hooks import ConfigureHook
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
        self.ethercat_driver_part.on_configure(self.context)

    def test_configure_from_disarmed_state(self):
        self._do_configure()

        assert self.child.handled_requests.mock_calls == [
            call.put("imageMode", "Continuous"),
            call.post("start"),
            call.when_value_matches("acquiring", True, None),
        ]

    def test_configure_from_armed_continuous_state(self):
        # Set the attributes to appear already armed in correct image mode
        self.set_attributes(self.child, acquiring=True, imageMode="Continuous")

        self._do_configure()

        # Call list should be empty
        assert self.child.handled_requests.mock_calls == []

    def test_configure_from_armed_but_not_continuous_state(self):
        # Set the attributes to appear already armed in wrong image mode
        self.set_attributes(self.child, acquiring=True, imageMode="Single")

        self._do_configure()

        assert self.child.handled_requests.mock_calls == [
            call.post("stop"),
            call.when_value_matches("acquiring", False, None),
            call.put("imageMode", "Continuous"),
            call.post("start"),
            call.when_value_matches("acquiring", True, None),
        ]

    # Patch the super setup() method so we only get desired calls
    @patch("malcolm.modules.ADCore.parts.DetectorDriverPart.setup")
    def test_setup(self, mocked_super_setup):
        # Check we hook on PreRun to arm and PostRunReady to abort
        mock_registrar = Mock(name="mock_registrar")
        self.ethercat_driver_part.setup(mock_registrar)

        assert mock_registrar.hook.called_once_with(
            ConfigureHook, self.ethercat_driver_part.on_configure
        )
