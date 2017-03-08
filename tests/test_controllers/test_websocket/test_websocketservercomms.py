import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from mock import MagicMock, patch, call

from malcolm.controllers.websocket import WebsocketServerComms
from malcolm.controllers.websocket.websocketservercomms import MalcWebSocketHandler,\
        MalcBlockHandler
from malcolm.core.request import Get, Post
from malcolm.core.response import Return, Error


class TestWSServerComms(unittest.TestCase):

    def setUp(self):
        self.p = MagicMock()

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_init(self, ioloop_mock, server_mock):
        self.WS = WebsocketServerComms(self.p, dict(port=1))

        self.assertEqual(self.p, self.WS.process)
        self.assertEqual(server_mock(), self.WS.server)
        self.assertEqual(ioloop_mock.current(), self.WS.loop)

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_listen_called(self, ioloop_mock, listen_mock):
        self.WS = WebsocketServerComms(self.p, dict(port=1))

        self.assertEqual(ioloop_mock.current(), self.WS.loop)

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_start(self, _, _2):
        self.p.spawn = MagicMock()

        self.WS = WebsocketServerComms(self.p, dict(port=1))
        self.WS.start()

        self.assertEqual([call(self.WS.send_loop), call(self.WS.loop.start)],
                         self.p.spawn.call_args_list)

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_stop(self, ioloop_mock, server_mock):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.p.spawn = MagicMock()

        self.WS = WebsocketServerComms(self.p, dict(port=1))
        self.WS.start()
        self.WS.stop()

        self.assertEqual([call(self.WS.server.stop), call(self.WS.loop.stop)],
                loop_mock.add_callback.call_args_list)
        self.p.spawn.return_value.wait.assert_not_called()

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_wait(self, ioloop_mock, server_mock):
        spawnable_mocks = [MagicMock(), MagicMock()]
        timeout = MagicMock()
        self.p.spawn = MagicMock(side_effect=spawnable_mocks)

        self.WS = WebsocketServerComms(self.p, dict(port=1))
        self.WS.start()
        self.WS.wait(timeout)

        spawnable_mocks[0].wait.assert_called_once_with(timeout=timeout)
        spawnable_mocks[1].wait.assert_called_once_with(timeout=timeout)

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_MWSH_on_message(self, ioloop_mock, server_mock):
        MWSH = MalcWebSocketHandler(MagicMock(), MagicMock())
        MWSH.servercomms = MagicMock()
        request = Get(None, None, ["block", "attr"])
        request.set_id(54)
        message = """{
        "typeid": "malcolm:core/Get:1.0",
        "id": 54,
        "path": ["block", "attr"]
        }"""
        MWSH.on_message(message)
        self.assertEquals(MWSH.servercomms.on_request.call_count, 1)
        actual = MWSH.servercomms.on_request.call_args[0][0]
        self.assertEquals(actual.to_dict(), request.to_dict())

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_on_request_with_process_name(self, _, _2):
        ws = WebsocketServerComms(self.p, dict(port=1))
        request = MagicMock(fields=dict(endpoint="anything"), path=[".", "blocks"])
        ws.on_request(request)
        self.p.q.put.assert_called_once_with(request)
        self.assertEqual(request.path, [self.p.name, "blocks"])

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client(self, _, _2):
        ws = WebsocketServerComms(self.p, dict(port=1))
        response = Return(11, MagicMock(spec=MalcWebSocketHandler), "me")
        ws._send_to_client(response)
        response.context.write_message.assert_called_once_with(
            '{"typeid": "malcolm:core/Return:1.0", "id": 11, "value": "me"}')

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client_return(self, _, _2):
        ws = WebsocketServerComms(self.p, dict(port=1))
        response = Return(11, MagicMock(), "me")
        ws._send_to_client(response)
        response.context.finish.assert_called_once_with(
            '"me"\n')

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client_error(self, _, _2):
        ws = WebsocketServerComms(self.p, dict(port=1))
        response = Error(11, MagicMock(), "bad")
        ws._send_to_client(response)

        response.context.set_status.assert_called_once_with(500, "bad")
        response.context.write_error.assert_called_once_with(500)

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client_unknown(self, _, _2):
        ws = WebsocketServerComms(self.p, dict(port=1))
        response = MagicMock()
        ws._send_to_client(response)

        response.context.set_status.assert_called_once_with(
            500, "Unknown response %s" % type(response))
        response.context.write_error.assert_called_once_with(500)

class TestMalcolmBlockHandler(unittest.TestCase):

    def test_get(self):
        mbh = MalcBlockHandler(MagicMock(), MagicMock())
        mbh.servercomms = MagicMock()
        mbh.get("test/endpoint/string")
        request = mbh.servercomms.on_request.call_args[0][0]
        self.assertIsInstance(request, Get)
        self.assertEqual(["test", "endpoint", "string"], request.path)
        self.assertIsNone(request.response_queue)

    def test_post(self):
        mbh = MalcBlockHandler(MagicMock(), MagicMock())
        mbh.servercomms = MagicMock()
        mbh.get_body_argument = MagicMock(side_effect=['{"test_json":12345}'])
        mbh.post("test/endpoint/string")
        request = mbh.servercomms.on_request.call_args[0][0]
        self.assertIsInstance(request, Post)
        self.assertEqual(["test", "endpoint", "string"], request.path)
        self.assertEqual({"test_json":12345}, request.parameters)
        self.assertIsNone(request.response_queue)

if __name__ == "__main__":
    unittest.main(verbosity=2)
