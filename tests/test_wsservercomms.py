import unittest
from collections import OrderedDict

from pkg_resources import require
require("mock")
require('tornado')
from mock import MagicMock, patch

from malcolm.wscomms.wsservercomms import WSServerComms
from malcolm.wscomms.wsservercomms import MalcolmWebSocketHandler


class TestWSServerComms(unittest.TestCase):

    def setUp(self):
        self.p = MagicMock()

    @patch('malcolm.wscomms.wsservercomms.Application')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_init(self, _, app_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        self.assertEqual("TestWebSocket", self.WS.name)
        self.assertEqual(self.p, self.WS.process)
        self.assertEqual(app_mock(), self.WS.WSApp)

    @patch('malcolm.wscomms.wsservercomms.Application.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_setup(self, ioloop_mock, listen_mock):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock

        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        listen_mock.assert_called_once_with(1)
        self.assertEqual(ioloop_mock.current(), self.WS.loop)
        self.assertEqual(self.WS.process,
                         self.WS.WSApp.handlers[0][1][0].handler_class.process)

    @patch('malcolm.wscomms.wsservercomms.Application.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_start(self, ioloop_mock, _):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.WS = WSServerComms("TestWebSocket", self.p, 1)
        self.WS.start_recv_loop()

        loop_mock.start.assert_called_once_with()

    @patch('malcolm.wscomms.wsservercomms.Application.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_stop(self, ioloop_mock, _):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.WS = WSServerComms("TestWebSocket", self.p, 1)
        self.WS.stop_recv_loop()

        loop_mock.stop.assert_called_once_with()

    @patch('malcolm.wscomms.wsservercomms.Request')
    @patch('malcolm.wscomms.wsservercomms.json')
    @patch('malcolm.wscomms.wsservercomms.Application.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_MWSH_on_message(self, _, _1, json_mock, request_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        message_dict = dict(name="TestMessage")
        json_mock.loads.return_value = message_dict

        request = MagicMock()
        request.context = self.WS.WSApp.handlers[0][1][0].handler_class
        request_mock.from_dict.return_value = request

        m = MagicMock()
        MWSH = MalcolmWebSocketHandler(m, m)
        self.WS.WSApp.handlers[0][1][0].handler_class.on_message(
            MWSH, "TestMessage")

        json_mock.loads.assert_called_once_with("TestMessage",
                                                object_pairs_hook=OrderedDict())
        request_mock.from_dict.assert_called_once_with(message_dict)
        self.p.handle_request.assert_called_once_with(request)

    @patch('malcolm.wscomms.wsservercomms.json')
    @patch('malcolm.wscomms.wsservercomms.Application.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_send_to_client(self, _, _2, json_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        response_mock = MagicMock()
        self.WS.send_to_client(response_mock)

        json_mock.dumps.assert_called_once_with(response_mock.to_dict())
        response_mock.context.write_message.assert_called_once_with(
            json_mock.dumps())
