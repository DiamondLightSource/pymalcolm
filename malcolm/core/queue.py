import signal

from malcolm.compat import queue, maybe_import_cothread, get_thread_ident
from .errors import TimeoutError


class Queue(object):
    """Threadsafe and cothreadsafe queue with gets in calling thread"""
    INTERRUPTED = object()

    def __init__(self, user_facing=False):
        self.user_facing = user_facing
        self.cothread = maybe_import_cothread()
        if self.cothread:
            self._event_queue = self.cothread.EventQueue()
            if user_facing:
                # Install a signal handler that will make sure we are the
                # thing that is interrupted
                def signal_exception(signum, frame):
                    self._event_queue.Signal(self.INTERRUPTED)

                signal.signal(signal.SIGINT, signal_exception)
        else:
            self._queue = queue.Queue()

    def get(self, timeout=None):
        if self.cothread is None:
            # No cothread, this is a queue.Queue()
            if self.user_facing and timeout is None:
                # If user facing then need to make it interruptable
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
        elif get_thread_ident() != self.cothread.scheduler_thread_id:
            # Not in cothread's thread, so need to use CallbackResult
            return self.cothread.CallbackResult(self.get, timeout)
        else:
            # In cothread's thread
            try:
                ret = self._event_queue.Wait(timeout=timeout)
            except self.cothread.Timedout:
                raise TimeoutError("Queue().get() timed out")
            else:
                if ret is self.INTERRUPTED:
                    raise KeyboardInterrupt()
                else:
                    return ret

    def put(self, value):
        if self.cothread is None:
            # No cothread, this is a queue.Queue()
            self._queue.put(value)
        elif self.cothread.scheduler_thread_id != get_thread_ident():
            # Not in cothread's thread, so need to use Callback
            self.cothread.Callback(self._event_queue.Signal, value)
        else:
            # In cothread's thread
            self._event_queue.Signal(value)

