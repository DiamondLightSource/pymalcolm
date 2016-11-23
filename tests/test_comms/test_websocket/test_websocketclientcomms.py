import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, patch, call

from malcolm.comms.websocket import WebsocketClientComms
from malcolm.core.response import Return
from malcolm.core.request import Get

params = dict(hostname="test", port=1)


class TestWSClientComms(unittest.TestCase):

    def setUp(self):
        self.p = MagicMock()

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_init(self, ioloop_mock):
        self.WS = WebsocketClientComms(self.p, params)
        self.assertEqual(self.p, self.WS.process)
        self.assertEqual("ws://test:1/ws", self.WS.url)
        self.assertEqual(ioloop_mock.current(), self.WS.loop)
        self.WS.loop.add_callback.assert_called_once_with(
            self.WS.recv_loop)

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_subscribe_initial(self, _):
        self.WS = WebsocketClientComms(self.p, params)
        self.WS.send_to_server = MagicMock()
        self.WS.subscribe_server_blocks()
        self.assertEqual(self.WS.send_to_server.call_count, 1)
        request = self.WS.send_to_server.call_args[0][0]
        self.assertEqual(request.id, 0)
        self.assertEqual(request.typeid, "malcolm:core/Subscribe:1.0")
        self.assertEqual(request.endpoint, [".", "blocks", "value"])
        self.assertEqual(request.delta, False)

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_on_message(self, _):
        self.WS = WebsocketClientComms(self.p, params)
        request = MagicMock()
        self.WS.requests[11] = request
        response = Return(11, MagicMock(), "me")
        message = """{
        "typeid": "malcolm:core/Return:1.0",
        "id": 11,
        "value": "me"
        }"""
        self.WS.on_message(message)
        self.assertEquals(request.response_queue.put.call_count, 1)
        actual = request.response_queue.put.call_args[0][0]
        self.assertEquals(actual.to_dict(), response.to_dict())

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_on_message_logs_exception(self, _):
        self.WS = WebsocketClientComms(self.p, params)
        self.WS.log_exception = MagicMock()
        self.WS.on_message("test")
        self.WS.log_exception.assert_called_once_with(
            'on_message(%r) failed', "test")

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_send_to_server(self, _):
        self.WS = WebsocketClientComms(self.p, params)
        self.WS.conn = MagicMock()
        request = Get(None, None, ["block", "attr"])
        request.set_id(54)
        self.WS.send_to_server(request)
        self.WS.conn.write_message.assert_called_once_with(
            '{"typeid": "malcolm:core/Get:1.0", "id": 54, "endpoint": ["block", "attr"]}')

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_start(self, ioloop_mock):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.WS = WebsocketClientComms(self.p, params)
        self.WS.process.spawn = MagicMock()
        self.WS.start()

        self.assertEqual([call(self.WS.send_loop), call(self.WS.loop.start)],
                         self.WS.process.spawn.call_args_list)

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_stop(self, ioloop_mock):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock

        self.WS = WebsocketClientComms(self.p, params)
        self.WS.start()
        loop_mock.reset_mock()
        self.WS.stop()

        loop_mock.add_callback.assert_called_once_with(
            ioloop_mock.current().stop)
        self.WS.process.spawn.return_value.assert_not_called()

    @patch('malcolm.comms.websocket.websocketclientcomms.IOLoop')
    def test_wait(self, _):
        spawnable_mocks = [MagicMock(), MagicMock()]
        timeout = MagicMock()

        self.WS = WebsocketClientComms(self.p, params)
        self.WS.process.spawn = MagicMock(side_effect=spawnable_mocks)
        self.WS.start()
        self.WS.wait(timeout)

        spawnable_mocks[0].wait.assert_called_once_with(timeout=timeout)
        spawnable_mocks[1].wait.assert_called_once_with(timeout=timeout)

if __name__ == "__main__":
    unittest.main(verbosity=2)
