import unittest
from mock import patch

from malcolm.core.loggable import Loggable


class TestLoggable(unittest.TestCase):

    @patch("malcolm.core.loggable.logging")
    def test_init(self, mock_logging):
        l = Loggable(foo="foo", bar="bat")
        mock_logging.getLogger.assert_called_once_with(
            "malcolm.core.loggable.Loggable.bat.foo")
        filter = l.log.addFilter.call_args[0][0]
        assert filter.fields == dict(foo="foo", bar="bat")

    @patch("malcolm.core.loggable.logging")
    def test_call_method_no_log_name(self, mock_logging):
        l = Loggable()
        l.log.debug("Something")
        mock_logging.getLogger.assert_called_once_with(
            "malcolm.core.loggable.Loggable")
        l.log.debug.assert_called_once_with("Something")
