import logging


class Loggable(object):
    """Utility class that provides a named logger for a class instance"""

    def __init__(self, logger_name):
        """
        Args:
            logger_name (str): Name of the logger to appear in log messages
        """
        super(Loggable, self).__init__()
        # The name that we will pass to the logger
        self._logger_name = None
        # The logger object itself
        self._logger = None
        self.set_logger_name(logger_name)

    def set_logger_name(self, logger_name):
        """Change the name of the logger that log_* should call

        Args:
            logger_name (str): Name of the logger to appear in log messages
        """
        self._logger_name = logger_name
        self._logger = logging.getLogger(self._logger_name)

    def log_debug(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.debug`"""
        self._logger.debug(msg, *args, **kwargs)

    def log_info(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.info`"""
        self._logger.info(msg, *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.warning`"""
        self._logger.warning(msg, *args, **kwargs)

    def log_error(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.error`"""
        self._logger.error(msg, *args, **kwargs)

    def log_exception(self, msg, *args, **kwargs):
        """Call :meth:`logging.Logger.exception`"""
        self._logger.exception(msg, *args, **kwargs)
