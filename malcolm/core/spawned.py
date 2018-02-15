import logging
from multiprocessing.pool import ThreadPool

from annotypes import TYPE_CHECKING

from malcolm.compat import maybe_import_cothread, get_thread_ident
from .queue import Queue

if TYPE_CHECKING:
    from typing import Callable, TypeVar, Tuple, Dict, Any, Union
    T = TypeVar("T")


# Create a module level logger
log = logging.getLogger(__name__)


class Spawned(object):
    NO_RESULT = object()

    def __init__(self, func, args, kwargs, use_cothread=True, thread_pool=None):
        # type: (Callable[..., Any], Tuple, Dict, bool, ThreadPool) -> None
        self.cothread = maybe_import_cothread()
        if use_cothread and not self.cothread:
            use_cothread = False
        self._result_queue = Queue()
        self._result = self.NO_RESULT  # type: Union[T, Exception]
        self._function = func
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
        # We finished running the function, so remove the reference to it
        # in case it's stopping garbage collection
        self._function = None
        self._result_queue.put(None)

    def wait(self, timeout=None):
        # type: (float) -> None
        # Only one person can wait on this at a time
        if self._result == self.NO_RESULT:
            self._result_queue.get(timeout)

    def ready(self):
        # type: () -> bool
        """Return True if the spawned result has returned or errored"""
        return self._result != self.NO_RESULT

    def get(self, timeout=None):
        # type: (float) -> T
        """Return the result or raise the error the function has produced"""
        self.wait(timeout)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result
