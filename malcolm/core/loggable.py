import logging


class Loggable:
    """Utility class that provides a named logger for a class instance"""

    log: logging.Logger

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
