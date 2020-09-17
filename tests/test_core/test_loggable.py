import unittest

from mock import patch

from malcolm.core.loggable import Loggable


class TestLoggable(unittest.TestCase):
    @patch("malcolm.core.loggable.logging")
    def test_init(self, mock_logging):
        loggable = Loggable()
        loggable.set_logger(foo="foo", bar="bat")
        mock_logging.getLogger.assert_called_once_with(
            "malcolm.core.loggable.Loggable.bat.foo"
        )
        assert mock_logging.LoggerAdapter.call_args[1] == {
            "extra": {"foo": "foo", "bar": "bat"}
        }

    def test_call_method_no_log_name(self):
        loggable = Loggable()
        with self.assertRaises(AttributeError):
            loggable.log.debug("Something")
