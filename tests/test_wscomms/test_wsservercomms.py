import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, patch, call

from malcolm.wscomms.wsservercomms import WSServerComms
from malcolm.wscomms.wsservercomms import MalcolmWebSocketHandler


class TestWSServerComms(unittest.TestCase):

    def setUp(self):
        self.p = MagicMock()

    @patch('malcolm.wscomms.wsservercomms.HTTPServer')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_init(self, ioloop_mock, server_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        self.assertEqual("TestWebSocket", self.WS.name)
        self.assertEqual(self.p, self.WS.process)
        self.assertEqual(server_mock(), self.WS.server)
        self.assertEqual(ioloop_mock.current(), self.WS.loop)

    @patch('malcolm.wscomms.wsservercomms.HTTPServer.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_listen_called(self, ioloop_mock, listen_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        self.assertEqual(ioloop_mock.current(), self.WS.loop)

    @patch('malcolm.wscomms.wsservercomms.HTTPServer.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_start(self, _, _2):
        self.p.spawn = MagicMock()

        self.WS = WSServerComms("TestWebSocket", self.p, 1)
        self.WS.start()

        self.assertEqual([call(self.WS.send_loop), call(self.WS.loop.start)],
                         self.p.spawn.call_args_list)

    @patch('malcolm.wscomms.wsservercomms.HTTPServer')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_stop(self, ioloop_mock, server_mock):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.p.spawn = MagicMock()

        self.WS = WSServerComms("TestWebSocket", self.p, 1)
        self.WS.start()
        self.WS.stop()

        self.assertEqual([call(self.WS.server.stop), call(self.WS.loop.stop)],
                loop_mock.add_callback.call_args_list)
        self.p.spawn.return_value.wait.assert_not_called()

    @patch('malcolm.wscomms.wsservercomms.HTTPServer')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_wait(self, ioloop_mock, server_mock):
        spawnable_mocks = [MagicMock(), MagicMock()]
        timeout = MagicMock()
        self.p.spawn = MagicMock(side_effect=spawnable_mocks)

        self.WS = WSServerComms("TestWebSocket", self.p, 1)
        self.WS.start()
        self.WS.wait(timeout)

        spawnable_mocks[0].wait.assert_called_once_with(timeout=timeout)
        spawnable_mocks[1].wait.assert_called_once_with(timeout=timeout)

    @patch('malcolm.wscomms.wsservercomms.Request')
    @patch('malcolm.wscomms.wsservercomms.json')
    @patch('malcolm.wscomms.wsservercomms.HTTPServer.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_MWSH_on_message(self, _, _1, json_mock, request_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        message_dict = dict(name="TestMessage")
        json_mock.loads.return_value = message_dict

        request = MagicMock()
        request.context = self.WS.server.request_callback.handlers[0][1][0].handler_class
        request_mock.from_dict.return_value = request

        m = MagicMock()
        MWSH = MalcolmWebSocketHandler(m, m)
        self.WS.server.request_callback.handlers[0][1][0].handler_class.on_message(
            MWSH, "TestMessage")

        json_mock.loads.assert_called_once_with("TestMessage",
                                                object_pairs_hook=OrderedDict)
        request_mock.from_dict.assert_called_once_with(message_dict)
        self.p.q.put.assert_called_once_with(request)

    @patch('malcolm.wscomms.wsservercomms.HTTPServer')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_on_request_with_process_name(self, _, _2):
        self.WS = WSServerComms("ws", self.p, 1)
        request = MagicMock(fields=dict(endpoint="anything"), endpoint=[".", "blocks"])
        self.WS.on_request(request)
        self.p.q.put.assert_called_once_with(request)
        self.assertEqual(request.endpoint, [self.p.name, "blocks"])

    @patch('malcolm.wscomms.wsservercomms.json')
    @patch('malcolm.wscomms.wsservercomms.HTTPServer.listen')
    @patch('malcolm.wscomms.wsservercomms.IOLoop')
    def test_send_to_client(self, _, _2, json_mock):
        self.WS = WSServerComms("TestWebSocket", self.p, 1)

        response_mock = MagicMock()
        self.WS.send_to_client(response_mock)

        json_mock.dumps.assert_called_once_with(response_mock.to_dict())
        response_mock.context.write_message.assert_called_once_with(
            json_mock.dumps())

if __name__ == "__main__":
    unittest.main(verbosity=2)
