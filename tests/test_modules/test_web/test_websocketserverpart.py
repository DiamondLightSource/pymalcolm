import os
import unittest

from mock import patch

from malcolm.modules.web.parts import WebsocketServerPart


@patch("malcolm.modules.web.parts.websocketserverpart.get_ip_validator")
@patch.object(WebsocketServerPart, "is_interface_up")
@patch.object(os, "listdir")
class TestWebsocketServerPart(unittest.TestCase):
    def test_on_report_handlers_with_subnet_validation_succeeds_for_one_good_interface(
        self, mock_os_listdir, mock_is_interface_up, mock_get_ip_validator
    ):
        # Return our fake interfaces
        mock_os_listdir.return_value = ["interface_1", "interface_2", "interface_3"]
        # The state of the interfaces - 2 are "up"
        mock_is_interface_up.side_effect = [True, False, True]
        # Return a pretend validator and one error
        mock_get_ip_validator.side_effect = ["validator_1", OSError()]

        websocket_server_part = WebsocketServerPart()

        info = websocket_server_part.on_report_handlers()

        # We should only have one validator
        assert info.kwargs["validators"] == ["validator_1"]

    def test_on_report_handlers_fails_with_subnet_validation_with_no_good_interfaces(
        self, mock_os_listdir, mock_is_interface_up, mock_get_ip_validator
    ):
        # Return our fake interfaces
        mock_os_listdir.return_value = ["interface_1", "interface_2", "interface_3"]
        # The state of the interfaces
        mock_is_interface_up.side_effect = [False, False, True]
        # Pretend validators
        mock_get_ip_validator.side_effect = [OSError()]

        websocket_server_part = WebsocketServerPart()

        self.assertRaises(AssertionError, websocket_server_part.on_report_handlers)
