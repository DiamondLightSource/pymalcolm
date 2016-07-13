import logging


class Loggable(object):
    """Utility class that provides a named logger for a class instance"""

    # The actual logging logger that produces our log messages
    _logger = None

    def _call_log_method(self, function, msg, *arg, **kwargs):
        if self._logger is None:
            raise ValueError("Attempt to log to a Loggable without first calling set_logger_name()")
        log_method = getattr(self._logger, function)
        log_method(msg, *arg, **kwargs)

    def set_logger_name(self, logger_name):
        """Change the name of the logger that log_* should call

        Args:
            logger_name (str): Name of the logger to appear in log messages
        """
        self._logger = logging.getLogger(logger_name)

    def log_debug(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.debug`"""
        self._call_log_method("debug", msg, *args, **kwargs)

    def log_info(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.info`"""
        self._call_log_method("info", msg, *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.warning`"""
        self._call_log_method("warning", msg, *args, **kwargs)

    def log_error(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.error`"""
        self._call_log_method("error", msg, *args, **kwargs)

    def log_exception(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.exception`"""
        self._call_log_method("exception", msg, *args, **kwargs)
