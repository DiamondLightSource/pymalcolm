import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, patch, call

from malcolm.core.servercomms import ServerComms
from malcolm.core.spawnable import Spawnable
from malcolm.core.syncfactory import SyncFactory


class TestServerComms(unittest.TestCase):

    def setUp(self):
        self.process = Mock()

    @patch("malcolm.core.servercomms.ServerComms.add_spawn_function")
    @patch("malcolm.core.servercomms.ServerComms.make_default_stop_func")
    def test_init(self, def_stop, add_func):
        server = ServerComms(self.process)
        self.process.create_queue.assert_called_once_with()
        self.assertEqual(
            server.q, self.process.create_queue.return_value)
        self.assertEquals(
            [call(server.send_loop, def_stop.return_value)],
            server.add_spawn_function.call_args_list)

    def test_not_implemented_error(self):
        server = ServerComms(self.process)
        self.assertRaises(NotImplementedError, server.send_to_client, Mock())

    def test_send_to_client_called(self):
        request = Mock()
        dummy_queue = Mock()
        dummy_queue.get = Mock(side_effect = [request, Spawnable.STOP])
        self.process.create_queue = Mock(return_value = dummy_queue)
        server = ServerComms(self.process)
        server.send_to_client = Mock()
        server.send_loop()
        server.send_to_client.assert_called_once_with(request)

    def test_send_to_process(self):
        self.process.q = Mock()
        server = ServerComms(self.process)
        request = Mock()
        server.send_to_process(request)
        self.process.q.put.assert_called_once_with(request)

    def test_send_logs_error(self):
        server = ServerComms(self.process)
        request = Mock()
        request.to_dict = Mock()
        server.q.get = Mock(side_effect = [request, server.STOP])
        server.log_exception = Mock()
        server.send_loop()
        server.log_exception.assert_called_once_with(
            "Exception sending response %s", request.to_dict.return_value)

if __name__ == "__main__":
    unittest.main(verbosity=2)
