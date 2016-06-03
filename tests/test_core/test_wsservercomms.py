import unittest

from pkg_resources import require

from malcolm.core.wscomms.wsservercomms import WSServerComms

require("mock")
from mock import MagicMock


class TestWSServerComms(unittest.TestCase):

    def test_send_to_client(self):
        process = MagicMock()
        ws = WSServerComms("Socket", process, object, None)

        # ws.send_to_client("Test")
