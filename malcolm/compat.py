import threading
import logging
import sys
from xml.etree import cElementTree as ET
import os

try:
    # python 2
    import Queue as queue  # noqa
except ImportError:
    # python 3
    import queue  # noqa

try:
    # python 2
    str_ = basestring
except NameError:
    # python 3
    str_ = str

try:
    # python 2
    long_ = long  # pylint:disable=invalid-name
except NameError:
    # python 3
    long_ = int  # pylint:disable=invalid-name

try:
    # ruamel exists
    from ruamel.ordereddict import ordereddict as OrderedDict
except ImportError:
    # fallback to slower collections
    from collections import OrderedDict


def et_to_string(element):
    xml = '<?xml version="1.0" ?>'
    try:
        xml += ET.tostring(element, encoding="unicode")
    except LookupError:
        xml += ET.tostring(element)
    return xml


def maybe_import_cothread():
    if os.environ.get("PYMALCOLM_USE_COTHREAD", "YES")[0].upper() == "Y":
        try:
            import cothread
        except ImportError:
            cothread = None
        return cothread


def get_pool_num_threads():
    if maybe_import_cothread():
        num_threads = 8
    else:
        num_threads = 128
    return num_threads


try:
    # Python2
    from thread import get_ident as get_thread_ident
except ImportError:
    # Python3
    from threading import get_ident as get_thread_ident


try:
    # Python3
    from logging import QueueHandler
except ImportError:
    # Python2
    class QueueHandler(logging.Handler):
        """Cut down version of the QueueHandler in Python3"""

        def __init__(self, queue):
            logging.Handler.__init__(self)
            self.queue = queue

        def prepare(self, record):
            # The format operation gets traceback text into record.exc_text
            # (if there's exception data), and also puts the message into
            # record.message. We can then use this to replace the original
            # msg + args, as these might be unpickleable. We also zap the
            # exc_info attribute, as it's no longer needed and, if not None,
            # will typically not be pickleable.
            self.format(record)
            record.msg = record.message
            record.args = None
            record.exc_info = None
            return record

        def emit(self, record):
            try:
                self.queue.put_nowait(self.prepare(record))
            except Exception:
                self.handleError(record)


if sys.version_info < (3, 5):
    # Python2 and old Python3 without respect_handler_level
    class QueueListener(object):
        """Cut down version of the QueueHandler in Python3.5"""
        _sentinel = None

        def __init__(self, queue, *handlers, **kwargs):
            self.queue = queue
            self.handlers = handlers
            self._thread = None

        def start(self):
            self._thread = threading.Thread(target=self._monitor)
            self._thread.daemon = True
            self._thread.start()

        def handle(self, record):
            """
            Handle a record.
            This just loops through the handlers offering them the record
            to handle.
            """
            for handler in self.handlers:
                if record.levelno >= handler.level:
                    handler.handle(record)

        def _monitor(self):
            """
            Monitor the queue for records, and ask the handler
            to deal with them.
            This method runs on a separate, internal thread.
            The thread will terminate if it sees a sentinel object in the queue.
            """
            q = self.queue
            has_task_done = hasattr(q, 'task_done')
            while True:
                record = q.get(True)
                if record is self._sentinel:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()

        def stop(self):
            self.queue.put_nowait(self._sentinel)
            self._thread.join()
            self._thread = None
else:
    # Python3.5 introduced respect_handler_level
    from logging.handlers import QueueListener
