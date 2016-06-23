from . import util
import unittest
from collections import OrderedDict

from pkg_resources import require
require('tornado')
from mock import MagicMock, patch, call

from malcolm.wscomms.wsclientcomms import WSClientComms


class TestWSServerComms(unittest.TestCase):

    def setUp(self):
        self.p = MagicMock()

    @patch('malcolm.wscomms.wsclientcomms.websocket_connect')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_init(self, ioloop_mock, connect_mock):
        self.WS = WSClientComms("TestWebSocket", self.p, "test/url")

        self.assertEqual("TestWebSocket", self.WS.name)
        self.assertEqual(self.p, self.WS.process)
        self.assertEqual("test/url", self.WS.url)
        self.assertEqual(ioloop_mock.current(), self.WS.loop)
        connect_mock.assert_called_once_with(self.WS.url, on_message_callback=self.WS.on_message)
        self.assertEqual(connect_mock(), self.WS.conn)

    @patch('malcolm.wscomms.wsclientcomms.Response')
    @patch('malcolm.wscomms.wsclientcomms.json')
    @patch('malcolm.wscomms.wsclientcomms.websocket_connect')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_on_message(self, _, _1, json_mock, response_mock):
        self.WS = WSClientComms("TestWebSocket", self.p, "test/url")

        message_dict = dict(name="TestMessage")
        json_mock.loads.return_value = message_dict

        response = MagicMock()
        response.id_ = 1
        response_mock.from_dict.return_value = response
        request_mock = MagicMock()
        self.WS.requests[1] = request_mock

        self.WS.on_message("TestMessage")

        json_mock.loads.assert_called_once_with("TestMessage",
                                                object_pairs_hook=OrderedDict)
        response_mock.from_dict.assert_called_once_with(message_dict)
        request_mock.response_queue.put.assert_called_once_with(response)

    @patch('malcolm.wscomms.wsclientcomms.json')
    @patch('malcolm.wscomms.wsclientcomms.websocket_connect')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_send_to_server(self, _, connect_mock, json_mock):
        self.WS = WSClientComms("TestWebSocket", self.p, "test/url")
        result_mock = MagicMock()
        connect_mock().result.return_value = result_mock
        dumps_mock = MagicMock()
        json_mock.dumps.return_value = dumps_mock

        request_mock = MagicMock()
        self.WS.send_to_server(request_mock)

        json_mock.dumps.assert_called_once_with(request_mock.to_dict())
        result_mock.write_message.assert_called_once_with(dumps_mock)

    @patch('malcolm.wscomms.wsclientcomms.websocket_connect')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_start(self, ioloop_mock, _):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock
        self.WS = WSClientComms("TestWebSocket", self.p, "test/url")
        self.WS.process.spawn = MagicMock()
        self.WS.start()

        self.assertEqual([call(self.WS.send_loop), call(self.WS.loop.start)],
                         self.WS.process.spawn.call_args_list)

    @patch('malcolm.wscomms.wsclientcomms.websocket_connect')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_stop(self, ioloop_mock, _):
        loop_mock = MagicMock()
        ioloop_mock.current.return_value = loop_mock

        self.WS = WSClientComms("TestWebSocket", self.p, "test/url")
        self.WS.start()
        self.WS.stop()

        loop_mock.add_callback.assert_called_once_with(
            ioloop_mock.current().stop)
        self.WS.process.spawn.return_value.assert_not_called()

    @patch('malcolm.wscomms.wsclientcomms.websocket_connect')
    @patch('malcolm.wscomms.wsclientcomms.IOLoop')
    def test_wait(self, ioloop_mock, _):
        spawnable_mocks = [MagicMock(), MagicMock()]
        timeout = MagicMock()

        self.WS = WSClientComms("TestWebSocket", self.p, "test/url")
        self.WS.process.spawn = MagicMock(side_effect=spawnable_mocks)
        self.WS.start()
        self.WS.wait(timeout)

        spawnable_mocks[0].wait.assert_called_once_with(timeout=timeout)
        spawnable_mocks[1].wait.assert_called_once_with(timeout=timeout)

if __name__ == "__main__":
    unittest.main(verbosity=2)
