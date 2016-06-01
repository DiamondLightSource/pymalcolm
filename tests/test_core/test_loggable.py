#!/bin/env dls-python
import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import patch

# module imports
from malcolm.core.loggable import Loggable


class TestLoggable(unittest.TestCase):

    @patch("malcolm.core.loggable.logging")
    def test_init(self, mock_logging):
        Loggable("foo")
        mock_logging.getLogger.assert_called_once_with("foo")

    @patch("malcolm.core.loggable.logging")
    def test_calls_logger_function(self, mock_logging):
        l = Loggable("bar")
        for n in "debug info warning error exception".split():
            m = getattr(l, "log_%s" % n)
            m("hello", n)
            getattr(l._logger, n).assert_called_once_with("hello", n)

if __name__ == "__main__":
    unittest.main(verbosity=2)
