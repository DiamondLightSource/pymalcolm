import unittest
import sys
import os
# import logging
# logging.basicConfig(level=logging.DEBUG)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock

# module imports
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory


class TestProcess(unittest.TestCase):

    def test_init(self):
        s = MagicMock()
        p = Process("proc", s)
        s.create_queue.assert_called_once_with()
        self.assertEqual(p.q, s.create_queue.return_value)

    def test_starting_process(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        b = MagicMock()
        b.name = "myblock"
        p.add_block(b)
        self.assertEqual(p._blocks, dict(myblock=b))
        p.start()
        request = MagicMock()
        request.endpoint = ["myblock", "foo"]
        p.q.put(request)
        # wait for spawns to have done their job
        p.stop()
        b.handle_request.assert_called_once_with(request)

    def test_error(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        p.log_exception = MagicMock()
        p.start()
        request = MagicMock()
        request.endpoint = ["anything"]
        request.to_dict.return_value = "<to_dict>"
        p.q.put(request)
        p.stop()
        p.log_exception.assert_called_once_with("Exception while handling %s",
                                                "<to_dict>")

if __name__ == "__main__":
    unittest.main(verbosity=2)
