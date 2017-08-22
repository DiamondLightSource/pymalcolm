import threading
import logging
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




class QueueHandler(logging.Handler):
    """
    This handler sends events to a queue. Typically, it would be used together
    with a multiprocessing Queue to centralise logging to file in one process
    (in a multi-process application), so as to avoid file write contention
    between processes.
    This code is new in Python 3.2, but this class can be copy pasted into
    user code for use with earlier Python versions.
    """

    def __init__(self, queue):
        """
        Initialise an instance, using the passed queue.
        """
        logging.Handler.__init__(self)
        self.queue = queue

    def enqueue(self, record):
        """
        Enqueue a record.
        The base implementation uses put_nowait. You may want to override
        this method if you want to use blocking, timeouts or custom queue
        implementations.
        """
        self.queue.put_nowait(record)

    def prepare(self, record):
        """
        Prepares a record for queuing. The object returned by this method is
        enqueued.
        The base implementation formats the record to merge the message
        and arguments, and removes unpickleable items from the record
        in-place.
        You might want to override this method if you want to convert
        the record to a dict or JSON string, or send a modified copy
        of the record while leaving the original intact.
        """
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
        """
        Emit a record.
        Writes the LogRecord to the queue, preparing it for pickling first.
        """
        try:
            self.enqueue(self.prepare(record))
        except Exception:
            self.handleError(record)


class QueueListener(object):
    """
    This class implements an internal threaded listener which watches for
    LogRecords being added to a queue, removes them and passes them to a
    list of handlers for processing.
    """
    _sentinel = None

    def __init__(self, queue, *handlers, **kwargs):
        """
        Initialise an instance with the specified queue and
        handlers.
        """
        self.queue = queue
        self.handlers = handlers
        self._thread = None
        self.respect_handler_level = kwargs.get("respect_handler_level", False)

    def dequeue(self, block):
        """
        Dequeue a record and return it, optionally blocking.
        The base implementation uses get. You may want to override this method
        if you want to use timeouts or work with custom queue implementations.
        """
        return self.queue.get(block)

    def start(self):
        """
        Start the listener.
        This starts up a background thread to monitor the queue for
        LogRecords to process.
        """
        self._thread = t = threading.Thread(target=self._monitor)
        t.daemon = True
        t.start()

    def prepare(self, record):
        """
        Prepare a record for handling.
        This method just returns the passed-in record. You may want to
        override this method if you need to do any custom marshalling or
        manipulation of the record before passing it to the handlers.
        """
        return record

    def handle(self, record):
        """
        Handle a record.
        This just loops through the handlers offering them the record
        to handle.
        """
        record = self.prepare(record)
        for handler in self.handlers:
            if not self.respect_handler_level:
                process = True
            else:
                process = record.levelno >= handler.level
            if process:
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
            try:
                record = self.dequeue(True)
                if record is self._sentinel:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                break

    def enqueue_sentinel(self):
        """
        This is used to enqueue the sentinel record.
        The base implementation uses put_nowait. You may want to override
        this
        method if you want to use timeouts or work with custom queue
        implementations.
        """
        self.queue.put_nowait(self._sentinel)

    def stop(self):
        """
        Stop the listener.
        This asks the thread to terminate, and then waits for it to do so.
        Note that if you don't call this before your application exits,
        there
        may be some records still left on the queue, which won't be
        processed.
        """
        self.enqueue_sentinel()
        self._thread.join()
        self._thread = None
