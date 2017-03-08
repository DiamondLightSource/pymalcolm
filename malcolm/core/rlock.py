import thread
import threading

from malcolm.compat import maybe_import_cothread
from .errors import WrongThreadError


class RLock(object):
    """A recursive lock object that works in threads and cothreads"""
    def __init__(self):
        self.cothread = maybe_import_cothread()
        if self.cothread is None or \
                self.cothread.scheduler_thread_id != thread.get_ident():
            self._lock = threading.RLock()
        else:
            self._lock = self.cothread.RLock()

    def _check_cothread_lock(self):
        if self.cothread and isinstance(self._lock, self.cothread.RLock):
            # can only use a cothread RLock from cothread's thread
            if self.cothread.scheduler_thread_id != thread.get_ident():
                raise WrongThreadError(
                    "Can only use a cothread RLock from cothread's thread")

    def acquire(self):
        self._check_cothread_lock()
        self._lock.acquire()

    __enter__ = acquire

    def release(self):
        self._check_cothread_lock()
        self._lock.release()

    def __exit__(self, t, v, tb):
        self.release()
