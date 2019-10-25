import logging.handlers
import json


class JsonSysLogHandler(logging.handlers.SysLogHandler):
    """Log Handler that sets extra fields onto the record as a json string"""

    fields_to_remove = ['message',
                        'msg',
                        'args',
                        'exc_info',
                        'relativeCreated',
                        'asctime',
                        'exc_text',
                        'created',
                        'threadName',
                        'msecs']

    def emit(self, record):
        """
        Emit a record adding the extra fields as a json string,
        removing any unwanted fields first.
        """
        extra = record.__dict__.copy()
        for field_to_remove in self.fields_to_remove:
            extra.pop(field_to_remove, None)

        record.extra = json.dumps(extra)
        super(JsonSysLogHandler, self).emit(record)
