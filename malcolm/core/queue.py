import thread

from malcolm.compat import queue, maybe_import_cothread
from .errors import TimeoutError


class Queue(object):
    """Threadsafe and cothreadsafe queue with gets in calling thread"""

    def __init__(self):
        self.cothread = maybe_import_cothread()
        if self.cothread:
            if self.cothread.scheduler_thread_id == thread.get_ident():
                # In cothread's thread
                self._event_queue = self.cothread.EventQueue()
            else:
                # Not in cothread's thread
                self._event_queue = self.cothread.ThreadedEventQueue()
        else:
            self._queue = queue.Queue()

    def get(self, timeout=None):
        if self.cothread is None:
            # No cothread, this is a queue.Queue()
            if timeout is None:
                # Need to make it interruptable
                # http://stackoverflow.com/a/212975
                while True:
                    try:
                        return self._queue.get(self, timeout=1000)
                    except queue.Empty:
                        pass
            else:
                try:
                    return self._queue.get(self, timeout=timeout)
                except queue.Empty:
                    raise TimeoutError("Queue().get() timed out")
        else:
            # If we're not in cothread's thread and using an EventQueue this
            # will fail in the Wait() call
            try:
                return self._event_queue.Wait(timeout=timeout)
            except self.cothread.Timedout:
                raise TimeoutError("Queue().get() timed out")

    def put(self, value):
        if self.cothread is None:
            # No cothread, this is a queue.Queue()
            self._queue.put(value)
        elif isinstance(self._event_queue, self.cothread.EventQueue) and \
                self.cothread.scheduler_thread_id != thread.get_ident():
            # Not in cothread's thread, but this is an EventQueue, so need to
            # use Callback
            self.cothread.Callback(self._event_queue.Signal, value)
        else:
            # Safe to call this as either it is a ThreadedEventQueue or we are
            # in cothread's thread
            self._event_queue.Signal(value)
