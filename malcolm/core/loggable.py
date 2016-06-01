import logging


class Loggable(object):
    """Utility class that provides a named logger for a class instance"""

    def __init__(self, logger_name):
        super(Loggable, self).__init__()
        # The name that we will pass to the logger
        self._logger_name = None
        # The logger object itself
        self._logger = None
        self.set_logger_name(logger_name)

    def set_logger_name(self, logger_name):
        """Change the name of the logger that log_* should call

        Args:
            logger_name (str): Name of the logger
        """
        self._logger_name = logger_name
        self._logger = logging.getLogger(self._logger_name)
        # set self.log_debug = self._logger.debug etc.
        for n in "debug warning info error exception".split():
            setattr(self, "log_%s" % n, getattr(self._logger, n))
