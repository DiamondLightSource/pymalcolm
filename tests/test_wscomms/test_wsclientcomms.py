import unittest
from collections import OrderedDict

from pkg_resources import require
require("mock")
require('tornado')
from mock import MagicMock, patch

from malcolm.wscomms.wsclientcomms import WSClientComms


class TestWSServerComms(unittest.TestCase):

    def setUp(self):
        self.p = MagicMock()

    @patch('malcolm.wscomms.wsclientcomms.Application')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_init(self, _, app_mock):
        self.WS = WSClientComms("TestWebSocket", self.p, 1)

        self.assertEqual("TestWebSocket", self.WS.name)
        self.assertEqual(self.p, self.WS.process)
        self.assertEqual(app_mock(), self.WS.WSApp)

    @patch('malcolm.wscomms.wsclientcomms.Application.listen')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_setup(self, ioloop_mock, listen_mock):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock

        self.WS = WSClientComms("TestWebSocket", self.p, 1)

        listen_mock.assert_called_once_with(1)
        self.assertEqual(ioloop_mock.current(), self.WS.loop)
        self.assertEqual(self.WS.process,
                         self.WS.WSApp.handlers[0][1][0].handler_class.process)

    @patch('malcolm.wscomms.wsclientcomms.Application.listen')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_start(self, ioloop_mock, _):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.WS = WSClientComms("TestWebSocket", self.p, 1)
        self.WS.start_recv_loop()

        loop_mock.start.assert_called_once_with()

    @patch('malcolm.wscomms.wsclientcomms.Application.listen')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_stop(self, ioloop_mock, _):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.WS = WSClientComms("TestWebSocket", self.p, 1)
        self.WS.stop_recv_loop()

        loop_mock.stop.assert_called_once_with()

    @patch('malcolm.wscomms.wsclientcomms.Response')
    @patch('malcolm.wscomms.wsclientcomms.json')
    @patch('malcolm.wscomms.wsclientcomms.Application.listen')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_MWSH_on_message(self, _, _1, json_mock, response_mock):
        self.WS = WSClientComms("TestWebSocket", self.p, 1)

        message_dict = dict(name="TestMessage")
        json_mock.loads.return_value = message_dict

        response = MagicMock()
        response.context = self.WS.WSApp.handlers[0][1][0].handler_class
        response_mock.from_dict.return_value = response

        m = MagicMock()
        MWSH = MalcolmWebSocketHandler(m, m)
        self.WS.WSApp.handlers[0][1][0].handler_class.on_message(
            MWSH, "TestMessage")

        json_mock.loads.assert_called_once_with("TestMessage",
                                                object_pairs_hook=OrderedDict())
        response_mock.from_dict.assert_called_once_with(message_dict)
        self.p.q.put.assert_called_once_with(response)

    @patch('malcolm.wscomms.wsclientcomms.json')
    @patch('malcolm.wscomms.wsclientcomms.Application.listen')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_send_to_client(self, _, _2, json_mock):
        self.WS = WSClientComms("TestWebSocket", self.p, 1)

        response_mock = MagicMock()
        self.WS.send_to_server(response_mock)

        json_mock.dumps.assert_called_once_with(response_mock.to_dict())
        response_mock.context.write_message.assert_called_once_with(
            json_mock.dumps())
