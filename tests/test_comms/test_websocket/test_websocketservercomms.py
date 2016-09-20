import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, patch, call

from malcolm.comms.websocket import WebsocketServerComms
from malcolm.comms.websocket.websocketservercomms import MalcWebSocketHandler,\
        MalcBlockHandler
from malcolm.core.request import Request, Get, Post
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

    @patch('malcolm.comms.websocket.websocketservercomms.deserialize_object')
    @patch('malcolm.comms.websocket.websocketservercomms.json')
    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_MWSH_on_message(self, _, _1, json_mock, deserialize_mock):
        self.WS = WebsocketServerComms(self.p, dict(port=1))

        message_dict = dict(name="TestMessage")
        json_mock.loads.return_value = message_dict

        request = MagicMock()
        request.context = self.WS.server.request_callback.handlers[0][1][1].handler_class
        deserialize_mock.return_value = request

        m = MagicMock()
        MWSH = MalcWebSocketHandler(m, m)
        self.WS.server.request_callback.handlers[0][1][1].handler_class.on_message(
            MWSH, "TestMessage")

        json_mock.loads.assert_called_once_with("TestMessage",
                                                object_pairs_hook=OrderedDict)
        deserialize_mock.assert_called_once_with(message_dict, Request)
        self.p.q.put.assert_called_once_with(request)

    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_on_request_with_process_name(self, _, _2):
        self.WS = WebsocketServerComms(self.p, dict(port=1))
        request = MagicMock(fields=dict(endpoint="anything"), endpoint=[".", "blocks"])
        self.WS.on_request(request)
        self.p.q.put.assert_called_once_with(request)
        self.assertEqual(request.endpoint, [self.p.name, "blocks"])

    @patch('malcolm.comms.websocket.websocketservercomms.json')
    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client(self, _, _2, json_mock):
        self.WS = WebsocketServerComms(self.p, dict(port=1))

        response_mock = MagicMock()
        response_mock.context = MagicMock(spec=MalcWebSocketHandler)
        self.WS._send_to_client(response_mock)

        json_mock.dumps.assert_called_once_with(response_mock.to_dict())
        response_mock.context.write_message.assert_called_once_with(
            json_mock.dumps())

    @patch('malcolm.comms.websocket.websocketservercomms.json')
    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client_return(self, _, _2, json_mock):
        ws = WebsocketServerComms(self.p, dict(port=1))
        response = MagicMock(spec=Return)
        response.value = MagicMock()
        response.context = MagicMock()
        ws._send_to_client(response)

        json_mock.dumps.assert_called_once_with(response.value.to_dict())
        response.context.finish.assert_called_once_with(
            json_mock.dumps.return_value + "\n")

    @patch('malcolm.comms.websocket.websocketservercomms.json')
    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client_error(self, _, _2, json_mock):
        ws = WebsocketServerComms(self.p, dict(port=1))
        response = MagicMock(spec=Error)
        response.context = MagicMock()
        response.message = MagicMock()
        ws._send_to_client(response)

        response.context.set_status.assert_called_once_with(
            500, response.message)
        response.context.write_error.assert_called_once_with(500)

    @patch('malcolm.comms.websocket.websocketservercomms.json')
    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
    def test_send_to_client_unknown(self, _, _2, json_mock):
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
        self.assertEqual(["test", "endpoint", "string"], request.endpoint)
        self.assertIsNone(request.response_queue)

    def test_post(self):
        mbh = MalcBlockHandler(MagicMock(), MagicMock())
        mbh.servercomms = MagicMock()
        mbh.get_body_argument = MagicMock(side_effect=['{"test_json":12345}'])
        mbh.post("test/endpoint/string")
        request = mbh.servercomms.on_request.call_args[0][0]
        self.assertIsInstance(request, Post)
        self.assertEqual(["test", "endpoint", "string"], request.endpoint)
        self.assertEqual({"test_json":12345}, request.parameters)
        self.assertIsNone(request.response_queue)

if __name__ == "__main__":
    unittest.main(verbosity=2)
