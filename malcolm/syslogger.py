import json
import logging.handlers


class JsonSysLogHandler(logging.handlers.SysLogHandler):
    """Log Handler that sets extra fields onto the record as a json string"""

    fields_to_remove = [
        "message",
        "msg",
        "args",
        "exc_info",
        "relativeCreated",
        "asctime",
        "exc_text",
        "created",
        "threadName",
        "msecs",
    ]

    def emit(self, record):
        """
        Emit a record adding the extra fields as a json string,
        removing any unwanted fields first.
        """
        extra = {
            k: v for k, v in record.__dict__.items() if k not in self.fields_to_remove
        }

        record.extra = json.dumps(extra)
        super().emit(record)
