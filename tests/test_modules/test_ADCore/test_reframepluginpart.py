from xml.etree import ElementTree

from mock import Mock, call, patch

from malcolm.core import DEFAULT_TIMEOUT, Context, Process
from malcolm.modules.ADCore.blocks import reframe_plugin_block
from malcolm.modules.ADCore.infos import FilePathTranslatorInfo
from malcolm.modules.ADCore.parts import ReframePluginPart
from malcolm.modules.ADCore.util import FRAME_TIMEOUT
from malcolm.testutil import ChildTestCase


class TestReframePluginPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            reframe_plugin_block,
            self.process,
            mri="BLOCK:REFRAME",
            prefix="prefix",
            suffix="suffix",
        )

    def tearDown(self):
        self.process.stop(timeout=2)

    def _create_part_and_start_process(self):
        self.o = ReframePluginPart(name="m", mri="BLOCK:REFRAME")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def _create_and_set_configure_mocks(self):
        wait_all_futures_mock = Mock(name="wait_all_futures_mock")
        self.start_future_mock = Mock(name="start_future_mock")
        self.child_mock = Mock(name="child_mock")
        self.child_mock.start_async.return_value = self.start_future_mock
        self.context.block_view = Mock(name="block_view_mock")
        self.context.wait_all_futures = wait_all_futures_mock
        self.context.block_view.return_value = self.child_mock

    def _check_configure_set_attributes(self, infos, frame_timeout, steps_to_do):
        assert infos is None
        assert self.o.frame_timeout == frame_timeout
        assert self.o.done_when_reaches == steps_to_do
        assert self.o.uniqueid_offset == 0
        assert self.o.start_future == self.start_future_mock

    def _check_configure_calls(self, steps_to_do, array_counter=0):
        self.child_mock.put_attribute_values_async.assert_called_once_with(
            dict(
                arrayCounter=array_counter,
                enableCallbacks=True,
                triggerMode="Multiple",
                triggerCount=steps_to_do,
                averageSamples="Yes",
            )
        )
        self.child_mock.when_value_matches.assert_called_once_with(
            "acquireMode", "Armed", timeout=DEFAULT_TIMEOUT
        )

    def test_configure_initial_configure_with_small_duration(self):
        # Set up the part
        self._create_part_and_start_process()
        # Configure mocks
        self._create_and_set_configure_mocks()
        # Configure args
        completed_steps = 0
        steps_to_do = 100
        generator = Mock(name="mock_generator")
        # 0 duration should double the default timeout
        generator.duration = 0

        # Call the configure method
        infos = self.o.on_configure(
            self.context, completed_steps, steps_to_do, generator
        )

        # Check attributes
        expected_timeout = 2 * FRAME_TIMEOUT
        self._check_configure_set_attributes(infos, expected_timeout, steps_to_do)

        # Check calls
        self._check_configure_calls(steps_to_do)

    def test_configure_initial_configure_with_large_duration(self):
        # Set up the part
        self._create_part_and_start_process()
        # Configure mocks
        self._create_and_set_configure_mocks()
        # Configure args
        completed_steps = 0
        steps_to_do = 25
        generator = Mock(name="mock_generator")
        # Set a duration larger than the default timeout
        generator.duration = FRAME_TIMEOUT + 10

        # Call the configure method
        infos = self.o.on_configure(
            self.context, completed_steps, steps_to_do, generator
        )

        # Check attributes
        expected_timeout = FRAME_TIMEOUT + generator.duration
        self._check_configure_set_attributes(infos, expected_timeout, steps_to_do)

        # Check calls
        self._check_configure_calls(steps_to_do)

    def test_configure_new_batch_large_duration(self):
        # Set up the part
        self._create_part_and_start_process()
        # Configure mocks
        self._create_and_set_configure_mocks()
        # Configure args
        completed_steps = 50
        steps_to_do = 250
        generator = Mock(name="mock_generator")
        # Set a duration larger than the default timeout
        generator.duration = FRAME_TIMEOUT + 10
        # Set attributes expected from initial run
        self.o.done_when_reaches = 50

        # Call the configure method
        infos = self.o.on_configure(
            self.context, completed_steps, steps_to_do, generator
        )

        # Check attributes
        expected_timeout = FRAME_TIMEOUT + generator.duration
        self._check_configure_set_attributes(infos, expected_timeout, steps_to_do)

        # Check calls
        self._check_configure_calls(steps_to_do, array_counter=completed_steps)

    def test_configure_new_batch_short_duration(self):
        # Set up the part
        self._create_part_and_start_process()
        # Configure mocks
        self._create_and_set_configure_mocks()
        # Configure args
        completed_steps = 16
        steps_to_do = 44
        generator = Mock(name="mock_generator")
        # Set a duration larger than the default timeout
        generator.duration = 0
        # Set attributes expected from initial run
        self.o.done_when_reaches = 16

        # Call the configure method
        infos = self.o.on_configure(
            self.context, completed_steps, steps_to_do, generator
        )

        # Check attributes
        expected_timeout = 2 * FRAME_TIMEOUT
        self._check_configure_set_attributes(infos, expected_timeout, steps_to_do)

        # Check calls
        self._check_configure_calls(steps_to_do, array_counter=completed_steps)

    def test_on_run(self):
        # Set up the part
        self._create_part_and_start_process()
        context_mock = Mock(name="mock_context")
        wait_for_plugin_mock = Mock(name="mock_wait_for_plugin")
        registrar_mock = Mock(name="mock_registrar")
        self.o.wait_for_plugin = wait_for_plugin_mock
        self.o.registrar = registrar_mock

        self.o.on_run(context_mock)

        # Not very exciting. Make sure it calls the wait_for_plugin method
        wait_for_plugin_mock.assert_called_once_with(
            context_mock, registrar_mock, event_timeout=self.o.frame_timeout
        )

    def test_stop_plugin(self):
        # Set up the part
        self._create_part_and_start_process()
        context_mock = Mock(name="mock_context")
        child_mock = Mock(name="mock_child")
        context_mock.block_view.return_value = child_mock

        self.o.stop_plugin(context_mock)

        # Check calls
        child_mock.assert_has_calls(
            [
                call.stop(),
                call.when_value_matches("acquireMode", "Idle", timeout=DEFAULT_TIMEOUT),
            ]
        )

    def test_on_abort(self):
        # Set up the part
        self._create_part_and_start_process()
        context_mock = Mock(name="mock_context")
        stop_plugin_mock = Mock(name="mock_stop_plugin")
        self.o.stop_plugin = stop_plugin_mock

        self.o.on_abort(context_mock)

        # Not very exciting. Make sure it calls the stop_plugin method
        stop_plugin_mock.assert_called_once_with(context_mock)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_reset")
    def test_on_reset(self, mock_reset_super):
        # Set up the part
        self._create_part_and_start_process()
        context_mock = Mock(name="mock_context")
        stop_plugin_mock = Mock(name="mock_stop_plugin")
        self.o.stop_plugin = stop_plugin_mock

        self.o.on_reset(context_mock)

        # Check we call on_reset and stop_plugin
        mock_reset_super.assert_called_once_with(context_mock)
        stop_plugin_mock.assert_called_once_with(context_mock)

    @patch("malcolm.modules.scanning.infos.RunProgressInfo")
    def test_update_completed_steps(self, run_progress_info_mock):
        # Set up the part
        self._create_part_and_start_process()
        value = 20
        registrar_mock = Mock(name="mock_registrar")

        self.o.update_completed_steps(value, registrar_mock)

        # Check the report call
        registrar_mock.report.assert_called_once_with(run_progress_info_mock(20))

    def test_wait_for_plugin(self):
        # Set up the part
        self._create_part_and_start_process()
        context_mock = Mock(name="mock_context")
        registrar_mock = Mock(name="mock_registrar")
        child_mock = Mock(name="mock_child")
        context_mock.block_view.return_value = child_mock
        event_timeout = 5

        self.o.wait_for_plugin(
            context_mock, registrar_mock, event_timeout=event_timeout
        )

        # Check calls
        child_mock.arrayCounterReadback.subscribe_value.assert_called_once_with(
            self.o.update_completed_steps, registrar_mock
        )
        context_mock.wait_all_futures.assert_called_once_with(
            self.o.start_future, event_timeout=event_timeout
        )
        child_mock.when_value_matches.assert_called_once_with(
            "triggerCountReadback", self.o.done_when_reaches, timeout=DEFAULT_TIMEOUT
        )
