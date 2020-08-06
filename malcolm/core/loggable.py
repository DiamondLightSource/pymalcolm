import logging
from typing import Union


class Loggable:
    """Utility class that provides a named logger for a class instance"""

    log: Union[logging.Logger, None] = None

    def set_logger(self, **fields):
        """Change the name of the logger that log.* should call

        Args:
            **fields: Extra fields to be logged. Logger name will be:
                ".".join([<module_name>, <cls_name>] + fields_sorted_on_key)
        """
        names = [self.__module__, self.__class__.__name__]
        for field, value in sorted(fields.items()):
            names.append(value)
        # names should be something like this for one field:
        #   ["malcolm.modules.scanning.controllers.runnablecontroller",
        #    "RunnableController", "BL45P-ML-SCAN-01"]
        logger = logging.getLogger(".".join(names))

        self.log = logging.LoggerAdapter(logger, extra=fields)

        return self.log

    def log_debug(self, message: str, *args, **kwargs) -> None:
        if self.log:
            self.log.debug(message, *args, **kwargs)

    def log_info(self, message: str, *args, **kwargs) -> None:
        if self.log:
            self.log.info(message, *args, **kwargs)

    def log_warning(self, message: str, *args, **kwargs) -> None:
        if self.log:
            self.log.warning(message, *args, **kwargs)

    def log_error(self, message: str, *args, **kwargs) -> None:
        if self.log:
            self.log.error(message, *args, **kwargs)

    def log_critical(self, message: str, *args, **kwargs) -> None:
        if self.log:
            self.log.critical(message, *args, **kwargs)

    def log_exception(self, message: str, *args, **kwargs) -> None:
        if self.log:
            self.log.exception(message, *args, **kwargs)
