import unittest
import logging

import malcolm.imalcolm
from malcolm.imalcolm import make_async_logging


class MyHandler(logging.Handler):
    emitted = []

    def emit(self, record):
        self.emitted.append(record)


# Need to put it somewhere importable so logging.config.dictConfig can find it
malcolm.imalcolm.MyHandler = MyHandler


class TestIMalcolm(unittest.TestCase):
    def test_logging(self):
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "mine": {
                    "class": "malcolm.imalcolm.MyHandler",
                    "level": "WARNING",
                },
            },
            "root": {
                "level": "DEBUG",
                "handlers": ["mine"],
            }
        }
        listener = make_async_logging(log_config)
        listener.start()
        logging.info("Good things happen")
        logging.warning("Bad things happen")
        listener.stop()
        assert len(MyHandler.emitted) == 1
        assert str(MyHandler.emitted[0]) == \
            '<LogRecord: root, 30, %s, 38, "Bad things happen">' % __file__



