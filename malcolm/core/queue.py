import thread

from malcolm.compat import queue, maybe_import_cothread
from .errors import TimeoutError


class Queue(object):
    """Threadsafe and cothreadsafe queue with gets in calling thread"""

    def __init__(self):
        self.cothread = maybe_import_cothread()
        if self.cothread:
            self._event_queue = self.cothread.EventQueue()
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
        elif thread.get_ident() != self.cothread.scheduler_thread_id:
            # Not in cothread's thread, so need to use CallbackResult
            return self.cothread.CallbackResult(self.get, timeout)
        else:
            # In cothread's thread
            try:
                return self._event_queue.Wait(timeout=timeout)
            except self.cothread.Timedout:
                raise TimeoutError("Queue().get() timed out")

    def put(self, value):
        if self.cothread is None:
            # No cothread, this is a queue.Queue()
            self._queue.put(value)
        elif self.cothread.scheduler_thread_id != thread.get_ident():
            # Not in cothread's thread, so need to use Callback
            self.cothread.Callback(self._event_queue.Signal, value)
        else:
            # In cothread's thread
            self._event_queue.Signal(value)

