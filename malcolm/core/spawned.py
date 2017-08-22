import logging

from malcolm.compat import maybe_import_cothread, get_thread_ident
from .queue import Queue


# Create a module level logger
log = logging.getLogger(__name__)


class Spawned(object):
    NO_RESULT = object()

    def __init__(self, function, args, kwargs, use_cothread=True,
                 thread_pool=None):
        self.cothread = maybe_import_cothread()
        if use_cothread and not self.cothread:
            use_cothread = False
        self._result_queue = Queue()
        self._result = self.NO_RESULT
        self._function = function
        self._args = args
        self._kwargs = kwargs

        if use_cothread:
            if self.cothread.scheduler_thread_id != get_thread_ident():
                # Spawning cothread from real thread
                self.cothread.Callback(
                    self.cothread.Spawn, self.catching_function)
            else:
                # Spawning cothread from cothread
                self.cothread.Spawn(self.catching_function)
        else:
            # Spawning real thread
            thread_pool.apply_async(self.catching_function)

    def catching_function(self):
        try:
            self._result = self._function(*self._args, **self._kwargs)
        except Exception as e:
            log.debug(
                "Exception calling %s(*%s, **%s)",
                self._function, self._args, self._kwargs, exc_info=True)
            self._result = e
        self._result_queue.put(None)

    def wait(self, timeout=None):
        # Only one person can wait on this at a time
        if self._result == self.NO_RESULT:
            self._result_queue.get(timeout)

    def ready(self):
        return self._result != self.NO_RESULT

    def get(self, timeout=None):
        self.wait(timeout)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result
