import unittest
from collections import OrderedDict

from . import util
from mock import Mock

from malcolm.core.clientcomms import ClientComms, CLIENT_STOP
from malcolm.core.syncfactory import SyncFactory

class TestClientComms(unittest.TestCase):
    def test_init(self):
        process = Mock()
        client = ClientComms("c", process)
        process.create_queue.assert_called_once_with()
        self.assertEqual(client.q, process.create_queue.return_value)

    def test_not_implemented_error(self):
        client = ClientComms("c", Mock())
        self.assertRaises(NotImplementedError, client.send_to_server, Mock())
        self.assertRaises(NotImplementedError, client.start_recv_loop)
        self.assertRaises(NotImplementedError, client.stop_recv_loop)

    def test_send_logs_error(self):
        client = ClientComms("c", Mock())
        client.send_to_server = Mock(side_effect=Exception)
        request = Mock()
        request.to_dict = Mock(return_value = "<to_dict>")
        client.q.get = Mock(side_effect = [request, CLIENT_STOP])
        client.log_exception = Mock()
        client.send_loop()
        client.log_exception.assert_called_once_with(
            "Exception sending request %s", "<to_dict>")

    def test_requests_are_stored(self):
        client = ClientComms("c", Mock())
        client._current_id = 1234
        request = Mock()
        client.send_to_server = Mock()
        client.q.get = Mock(side_effect = [request, CLIENT_STOP])
        client.send_loop()
        expected = OrderedDict({1234 : request})
        self.assertEquals(expected, client.requests)

    def test_loop_starts(self):
        process = Mock(spawn = lambda x: x())
        client = ClientComms("c", process)
        client.send_loop = Mock()
        client.start_recv_loop = Mock()
        client.log_exception = Mock()
        client.start()
        client.send_loop.assert_called_once_with()
        client.start_recv_loop.assert_called_once_with()
        client.log_exception.assert_not_called()

    def test_sends_to_server(self):
        client = ClientComms("c", Mock())
        client.send_to_server = Mock()
        request = Mock()
        client.q.get = Mock(side_effect = [request, CLIENT_STOP])
        client.log_exception = Mock()
        client.send_loop()
        client.send_to_server.assert_called_once_with(request)
        client.log_exception.assert_not_called()

    def test_start_stop(self):
        sync_factory = SyncFactory("s")
        process = Mock()
        process.spawn = sync_factory.spawn
        process.create_queue = sync_factory.create_queue
        client = ClientComms("c", process)
        client.send_loop = Mock(side_effect = client.send_loop)
        client.start_recv_loop = Mock()
        client.stop_recv_loop = Mock()
        client.log_exception = Mock()
        client.start()
        self.assertFalse(client._send_spawned.ready())
        client.start_recv_loop.assert_called_once_with()
        client.stop(0.1)
        self.assertTrue(client._send_spawned.ready())
        client.send_loop.assert_called_once_with()
        client.stop_recv_loop.assert_called_once_with()
        client.log_exception.assert_not_called()

    def test_request_id_provided(self):
        client = ClientComms("c", Mock())
        client._current_id = 1234
        client.send_to_server = Mock()
        request_1 = Mock(id_ = None)
        request_2 = Mock(id_ = None)
        client.q.get = Mock(side_effect = [request_1, request_2, CLIENT_STOP])
        client.send_loop()
        self.assertEqual(1234, request_1.id_)
        self.assertEqual(1235, request_2.id_)

    def test_send_to_caller(self):
        request = Mock(response_queue=Mock(), id_=1234)
        client = ClientComms("c", Mock())
        client.requests = {1234:request}
        response = Mock(id_ = 1234)
        client.send_to_caller(response)
        request.response_queue.put.assert_called_once_with(response)

if __name__ == "__main__":
    unittest.main(verbosity=2)
