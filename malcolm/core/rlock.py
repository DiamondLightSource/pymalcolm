import threading

from malcolm.compat import maybe_import_cothread, get_thread_ident
from .errors import WrongThreadError


class RLock(object):
    """A recursive lock object that works in threads and cothreads"""
    def __init__(self, use_cothread=True):
        if use_cothread:
            self.cothread = maybe_import_cothread()
        else:
            self.cothread = None
        if self.cothread:
            if self.cothread.scheduler_thread_id == get_thread_ident():
                self._lock = self.cothread.RLock()
            else:
                self._lock = self.cothread.CallbackResult(self.cothread.RLock)
        else:
            self._lock = threading.RLock()
            self._check_cothread_lock = lambda: None

    def _check_cothread_lock(self):
        if self.cothread.scheduler_thread_id != get_thread_ident():
            # can only use a cothread RLock from cothread's thread
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

