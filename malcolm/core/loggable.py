import logging


class FieldFilter(object):
    def __init__(self, fields):
        assert "name" not in fields, \
            "Can't log custom field called name, it overwrites the logger name!"
        self.fields = fields

    def filter(self, record):
        for k, v in self.fields.items():
            setattr(record, k, v)
        return True


class Loggable(object):
    """Utility class that provides a named logger for a class instance"""

    # The actual logging logger that produces our log messages
    _log = None

    @property
    def log(self):
        if self._log is None:
            # Get a the default logger name
            self.set_logger_extra()
        return self._log

    def set_logger_extra(self, **fields):
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
        self._log = logging.getLogger(".".join(names))
        if fields:
            self._log.addFilter(FieldFilter(fields))
