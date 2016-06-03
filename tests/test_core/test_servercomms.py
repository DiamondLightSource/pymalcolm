import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import Mock

from malcolm.core.servercomms import ServerComms, SERVER_STOP
from malcolm.core.syncfactory import SyncFactory

class TestServerComms(unittest.TestCase):

    def setUp(self):
        self.process = Mock()

    def test_init(self):
        server = ServerComms("server", self.process)
        self.process.create_queue.assert_called_once_with()
        self.assertEqual(
            server.q, self.process.create_queue.return_value)

    def test_not_implemented_error(self):
        server = ServerComms("server", self.process)
        self.assertRaises(NotImplementedError, server.send_to_client)
        self.assertRaises(NotImplementedError, server.start_recv_loop)
        self.assertRaises(NotImplementedError, server.stop_recv_loop)

    def test_loop_starts(self):
        self.process.spawn = lambda x: x()
        server = ServerComms("server", self.process)
        server.send_loop = Mock()
        server.start_recv_loop = Mock()
        server.start()
        server.send_loop.assert_called_once_with()
        server.start_recv_loop.assert_called_once_with()

    def test_loop_stops(self):
        self.process.spawn = lambda x: x()
        self.process.create_queue = Mock(
            return_value=Mock(get=Mock(return_value=SERVER_STOP)))
        server = ServerComms("server", self.process)
        server.start_recv_loop = Mock()
        server.stop_recv_loop = Mock()
        server.send_loop = Mock(side_effect = server.send_loop)
        server.start()
        server.send_loop.assert_called_once_with()

    def test_start_stop(self):
        self.process.sync_factory = SyncFactory("s")
        self.process.spawn = self.process.sync_factory.spawn
        self.process.create_queue = self.process.sync_factory.create_queue
        server = ServerComms("server", self.process)
        server.send_loop = Mock(side_effect = server.send_loop)
        server.start_recv_loop = Mock()
        server.stop_recv_loop = Mock()
        server.start()
        self.assertFalse(server._send_spawned.ready())
        server.start_recv_loop.assert_called_once_with()
        server.stop(0.1)
        self.assertTrue(server._send_spawned.ready())
        server.send_loop.assert_called_once_with()
        server.stop_recv_loop.assert_called_once_with()

    def test_send_to_client(self):
        request = Mock()
        dummy_queue = Mock()
        dummy_queue.get = Mock(side_effect = [request, SERVER_STOP])
        self.process.create_queue = Mock(return_value = dummy_queue)
        self.process.spawn = Mock(side_effect = lambda x: x())
        server = ServerComms("server", self.process)
        server.send_to_client = Mock(
            side_effect = server.send_to_client)
        server.start_recv_loop = Mock()
        server.start()
        server.send_to_client.assert_called_once_with(request)

    def test_send_to_process(self):
        self.process.q = Mock()
        server = ServerComms("server", self.process)
        request = Mock()
        server.send_to_process(request)
        self.process.q.put.assert_called_once_with(request)

if __name__ == "__main__":
    unittest.main(verbosity=2)
