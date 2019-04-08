import inspect
import threading
import logging
import sys
from xml.etree import cElementTree as ET
import os


if sys.version_info < (3,):
    # python 2
    import Queue as queue
else:
    # python 3
    import queue

if sys.version_info < (3,):
    # python 2
    str_ = basestring

    def clean_repr(x):
        if isinstance(x, unicode):
            return repr(x)[1:]
        else:
            return repr(x)
else:
    # python 3
    str_ = str
    clean_repr = repr

if sys.version_info < (3,):
    # python 2
    long_ = long  # pylint:disable=invalid-name
else:
    # python 3
    long_ = int  # pylint:disable=invalid-name


try:
    # ruamel exists, us this OrderedDict as it is faster
    from ruamel.ordereddict import ordereddict as OrderedDict
except ImportError:
    # Fallback to slower collections one
    from collections import OrderedDict


def get_profiler_dir():
    return os.environ.get("PYMALCOLM_PROFILER_DIR", "/tmp/imalcolm_profiles")


def get_stack_size():
    return int(os.environ.get("PYMALCOLM_STACK_SIZE", "0"))


def getargspec(f):
    if sys.version_info < (3,):
        args, varargs, keywords, defaults = inspect.getargspec(f)
    else:
        # Need to use fullargspec in case there are annotations
        args, varargs, keywords, defaults = inspect.getfullargspec(f)[:4]
    return inspect.ArgSpec(args, varargs, keywords, defaults)


def et_to_string(element):
    # type: (ET.Element) -> str
    xml = '<?xml version="1.0" ?>'
    try:
        xml += ET.tostring(element, encoding="unicode")
    except LookupError:
        xml += ET.tostring(element)
    return xml


# Exception handling from future.utils
if sys.version_info < (3,):
    exec('''
def raise_with_traceback(exc, traceback=Ellipsis):
    if traceback == Ellipsis:
        _, _, traceback = sys.exc_info()
    raise exc, None, traceback
''')
else:
    def raise_with_traceback(exc, traceback=Ellipsis):
        if traceback == Ellipsis:
            _, _, traceback = sys.exc_info()
        raise exc.with_traceback(traceback)

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
