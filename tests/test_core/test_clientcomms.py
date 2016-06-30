import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import Mock, patch, call

from malcolm.core.clientcomms import ClientComms
from malcolm.core.syncfactory import SyncFactory


class TestClientComms(unittest.TestCase):
    @patch("malcolm.core.clientcomms.ClientComms.add_spawn_function")
    @patch("malcolm.core.clientcomms.ClientComms.make_default_stop_func")
    def test_init(self, def_stop, add_func):
        process = Mock()
        client = ClientComms("c", process)
        process.create_queue.assert_called_once_with()
        self.assertEqual(client.q, process.create_queue.return_value)
        spawn_function_calls = client.add_spawn_function.call_args_list
        self.assertEquals(
            [call(client.send_loop, def_stop.return_value)],
            spawn_function_calls)

    def test_not_implemented_error(self):
        client = ClientComms("c", Mock())
        self.assertRaises(NotImplementedError, client.send_to_server, Mock())

    def test_send_logs_error(self):
        client = ClientComms("c", Mock())
        client.send_to_server = Mock(side_effect=Exception)
        request = Mock()
        request.to_dict = Mock(return_value = "<to_dict>")
        client.q.get = Mock(side_effect = [request, client.STOP])
        client.log_exception = Mock()
        client.send_loop()
        client.log_exception.assert_called_once_with(
            "Exception sending request %s", "<to_dict>")

    def test_requests_are_stored(self):
        client = ClientComms("c", Mock())
        client._current_id = 1234
        request = Mock()
        def f(id_):
            request.id_ = id_
        request.set_id.side_effect = f
        client.send_to_server = Mock()
        client.q.get = Mock(side_effect = [request, client.STOP])
        client.send_loop()
        expected = OrderedDict({1234 : request})
        self.assertEquals(expected, client.requests)

    def test_sends_to_server(self):
        client = ClientComms("c", Mock())
        client.send_to_server = Mock()
        request = Mock()
        client.q.get = Mock(side_effect = [request, client.STOP])
        client.log_exception = Mock()
        client.send_loop()
        client.send_to_server.assert_called_once_with(request)
        client.log_exception.assert_not_called()

    def test_request_id_provided(self):
        client = ClientComms("c", Mock())
        client._current_id = 1234
        client.send_to_server = Mock()
        request_1 = Mock(id_ = None)
        request_2 = Mock(id_ = None)
        client.q.get = Mock(side_effect = [request_1, request_2, client.STOP])
        client.send_loop()
        request_1.set_id.assert_called_once_with(1234)
        request_2.set_id.assert_called_once_with(1235)

    def test_send_to_caller(self):
        request = Mock(response_queue=Mock(), id_=1234)
        client = ClientComms("c", Mock())
        client.requests = {1234:request}
        response = Mock(id_ = 1234)
        client.send_to_caller(response)
        request.response_queue.put.assert_called_once_with(response)

if __name__ == "__main__":
    unittest.main(verbosity=2)
