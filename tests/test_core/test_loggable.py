import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import patch

from malcolm.core.loggable import Loggable


class TestLoggable(unittest.TestCase):

    @patch("malcolm.core.loggable.logging")
    def test_init(self, mock_logging):
        l = Loggable()
        l.set_logger_name("foo")
        mock_logging.getLogger.assert_called_once_with("foo")

    @patch("malcolm.core.loggable.logging")
    def test_call_method_no_log_name(self, mock_logging):
        l = Loggable()
        self.assertRaises(ValueError, l.log_info, "msg")

    @patch("malcolm.core.loggable.logging")
    def test_calls_logger_function(self, mock_logging):
        l = Loggable()
        l.set_logger_name("bar")
        for n in "debug info warning error exception".split():
            m = getattr(l, "log_%s" % n)
            m("hello", n)
            getattr(l._logger, n).assert_called_once_with("hello", n)

if __name__ == "__main__":
    unittest.main(verbosity=2)
