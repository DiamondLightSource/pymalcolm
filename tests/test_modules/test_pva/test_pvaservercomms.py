import unittest
from collections import OrderedDict

from mock import MagicMock, call, patch

from malcolm.core import Error, Method
from malcolm.modules.pva.controllers import BlockHandler, PvaServerComms


class TestBlockHandler(unittest.TestCase):
    def setUp(self):
        self.controller_mock = MagicMock(name="controller_mock")
        self.block_handler = BlockHandler(self.controller_mock)

        self.pv_mock = MagicMock(name="pv_mock")
        self.op_mock = MagicMock(name="op_mock")

        # Set up the value mock and ID
        self.value_mock = MagicMock(name="value_mock")
        self.value_mock.getID.return_value = "value_id"
        self.op_mock.value.return_value = self.value_mock

        # Set up changed fields mock
        changed_fields_mock = MagicMock(name="changed_fields_mock")
        changed_fields_mock.intersection.return_value = ["value"]
        self.value_mock.changedSet.return_value = changed_fields_mock

    @patch("malcolm.modules.pva.controllers.pvaservercomms.Post")
    def test_rpc_handle_post_response_nested_function_with_bad_response(
        self, post_mock
    ):

        # Set up the mocked Post class to return a mocked instance
        post_instance_mock = MagicMock(name="post_instance_mock")
        post_mock.return_value = post_instance_mock

        # Mock the callback method
        response_mock = MagicMock(name="response_mock")
        response_mock.to_dict.return_value = "this is a bad response indeed"

        def mock_set_callback_func(*args):
            args[0](response_mock)

        post_instance_mock.set_callback.side_effect = mock_set_callback_func

        # Set method name
        method = "method_name"
        self.block_handler.field = method

        # Mock controller to return method
        view_mock = MagicMock(name="view_mock", spec=Method)
        self.controller_mock.block_view.return_value = {method: view_mock}

        # Now we can call the RPC method
        self.block_handler.rpc(self.pv_mock, self.op_mock)

        # Perform our checks
        bad_response_message = "BadResponse: this is a bad response indeed"
        self.op_mock.done.assert_called_once_with(error=bad_response_message)

        ordered_dict = OrderedDict([("typeid", "value_id")])
        rpc_call = call(
            f"{self.controller_mock.mri}: RPC method {method} called with params "
            f"{ordered_dict}"
        )

        response_call = call(
            f"{self.controller_mock.mri}: RPC method {method} got a bad response "
            f"({bad_response_message})"
        )
        self.controller_mock.log.debug.assert_has_calls([rpc_call, response_call])

    @patch("malcolm.modules.pva.controllers.pvaservercomms.convert_value_to_dict")
    @patch("malcolm.modules.pva.controllers.pvaservercomms.Put")
    def test_put_method_handle_put_response_nested_function_handles_BadResponse(
        self, put_mock, convert_value_to_dict_mock
    ):
        # Set field
        self.block_handler.field = "field"

        # Set up the mocked Post class to return a mocked instance
        put_instance_mock = MagicMock(name="put_instance_mock")
        put_mock.return_value = put_instance_mock

        # Mock the callback method
        response_mock = MagicMock(name="response_mock")
        response_mock.to_dict.return_value = "this is a bad response indeed"

        def mock_set_callback_func(*args):
            args[0](response_mock)

        put_instance_mock.set_callback.side_effect = mock_set_callback_func

        # Now we can call the put method
        self.block_handler.put(self.pv_mock, self.op_mock)

        # Perform our checks
        put_mock.assert_called_once()
        put_instance_mock.set_callback.assert_called_once()

        bad_response_message = "BadResponse: this is a bad response indeed"
        self.op_mock.done.assert_called_once_with(error=bad_response_message)

    @patch("malcolm.modules.pva.controllers.pvaservercomms.convert_value_to_dict")
    @patch("malcolm.modules.pva.controllers.pvaservercomms.Put")
    def test_put_method_handle_put_response_nested_function_handles_Error(
        self, put_mock, convert_value_to_dict_mock
    ):
        # Set field
        self.block_handler.field = "field"

        # Set up the mocked Post class to return a mocked instance
        put_instance_mock = MagicMock(name="put_instance_mock")
        put_mock.return_value = put_instance_mock

        # Mock the callback method
        response_mock = MagicMock(name="response_mock", spec=Error)
        error_message = "Oh dear, an error was encountered"
        response_mock.message = error_message

        def mock_set_callback_func(*args):
            args[0](response_mock)

        put_instance_mock.set_callback.side_effect = mock_set_callback_func

        # Now we can call the put method
        self.block_handler.put(self.pv_mock, self.op_mock)

        # Perform our checks
        put_mock.assert_called_once()
        put_instance_mock.set_callback.assert_called_once()

        self.op_mock.done.assert_called_once_with(
            error="str: {msg}".format(msg=error_message)
        )


class TestPvaServerComms(unittest.TestCase):
    def setUp(self):
        self.pva_server_comms = PvaServerComms("TEST:COMMS")

    def test_testChannel_returns_True_if_channel_is_in_published(self):
        channel_name = "CHANNEL1"
        self.pva_server_comms._published.add(channel_name)

        self.assertEqual(True, self.pva_server_comms.testChannel(channel_name))

    def test_testChannel_returns_True_if_channel_of_field_is_in_published(self):
        channel_name = "CHANNEL1"
        field = "FIELD1"
        self.pva_server_comms._published.add(channel_name)

        self.assertEqual(
            True,
            self.pva_server_comms.testChannel(
                "{channel}.{field}".format(channel=channel_name, field=field)
            ),
        )

    def test_testChannel_returns_False_if_channel_is_not_in_published(self):
        channel_name = "CHANNEL1"

        self.assertEqual(False, self.pva_server_comms.testChannel(channel_name))

    def test_testChannel_returns_False_if_channel_of_field_is_not_in_published(self):
        channel_name = "CHANNEL1"
        field = "FIELD1"

        self.assertEqual(
            False,
            self.pva_server_comms.testChannel(
                "{channel}.{field}".format(channel=channel_name, field=field)
            ),
        )

    def test_make_channel_raises_NameError_for_bad_channel_name(self):
        channel_name = "CHANNEL1"
        source = "Source1"

        self.assertRaises(
            NameError, self.pva_server_comms._make_channel, channel_name, source
        )

    def test_makeChannel_returns_CallbackResult(self):
        # Add channel
        channel_name = "CHANNEL1"
        source = "Source1"
        self.pva_server_comms._published.add(channel_name)
        # Mock make_channel method
        mock_make_channel = MagicMock(name="mock_make_channel")
        mock_make_channel.return_value = "return_value"
        self.pva_server_comms._make_channel = mock_make_channel

        result = self.pva_server_comms.makeChannel(channel_name, source)

        self.assertEqual("return_value", result)
        mock_make_channel.assert_called_once_with(channel_name, source)

    @patch("malcolm.modules.pva.controllers.pvaservercomms.cothread.CallbackResult")
    def test_makeChannel_calls_cothread_CallbackResult(self, callback_mock):
        # Add channel
        channel_name = "CHANNEL1"
        source = "Source1"
        self.pva_server_comms._published.add(channel_name)

        self.pva_server_comms.makeChannel(channel_name, source)

        callback_mock.assert_called_once_with(
            self.pva_server_comms._make_channel,
            channel_name,
            source,
            callback_timeout=1.0,
        )
