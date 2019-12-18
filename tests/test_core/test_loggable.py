import unittest
from mock import patch

from malcolm.core.loggable import Loggable


class TestLoggable(unittest.TestCase):

    @patch("malcolm.core.loggable.logging")
    def test_init(self, mock_logging):
        l = Loggable()
        l.set_logger(foo="foo", bar="bat")
        mock_logging.getLogger.assert_called_once_with(
            "malcolm.core.loggable.Loggable.bat.foo")
        assert mock_logging.LoggerAdapter.call_args[1] == \
            {'extra': {'foo': 'foo', 'bar': 'bat'}}

    def test_call_method_no_log_name(self):
        l = Loggable()
        with self.assertRaises(AttributeError):
            l.log.debug("Something")
