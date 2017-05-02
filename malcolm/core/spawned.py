import logging
import thread

from malcolm.compat import maybe_import_cothread
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

        def catching_function():
            try:
                result = function(*args, **kwargs)
            except Exception as result:
                log.debug(
                    "Exception calling %s(*%s, **%s)", function, args, kwargs,
                    exc_info=True)
            self._result_queue.put(result)

        if use_cothread:
            if self.cothread.scheduler_thread_id != thread.get_ident():
                # Spawning cothread from real thread
                self.cothread.Callback(self.cothread.Spawn, catching_function)
            else:
                # Spawning cothread from cothread
                self.cothread.Spawn(catching_function)
        else:
            # Spawning real thread
            thread_pool.apply_async(catching_function)

    def wait(self, timeout=None):
        if not self.ready():
            self._result = self._result_queue.get(timeout)

    def ready(self):
        return self._result != self.NO_RESULT

    def get(self, timeout=None):
        if not self.ready():
            self.wait(timeout)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result
