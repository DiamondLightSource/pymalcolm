import logging
import time
from threading import get_ident as get_thread_ident
from typing import Any, Callable, Dict, Tuple, TypeVar, Union

import cothread

from malcolm.compat import get_stack_size

from .errors import TimeoutError

T = TypeVar("T")


# Make a module level logger
log = logging.getLogger(__name__)

# Re-export
sleep = cothread.Sleep
RLock = cothread.RLock


class Spawned:
    """Internal object keeping track of a spawned function"""

    NO_RESULT = object()

    def __init__(self, func: Callable[..., Any], args: Tuple, kwargs: Dict) -> None:
        self._result_queue = Queue()
        self._result: Union[Any, Exception] = self.NO_RESULT
        self._function = func
        self._args = args
        self._kwargs = kwargs
        cothread.Spawn(self.catching_function, stack_size=get_stack_size())

    def catching_function(self):
        try:
            self._result = self._function(*self._args, **self._kwargs)
        except Exception as e:
            log.debug(
                "Exception calling %s(*%s, **%s)",
                self._function,
                self._args,
                self._kwargs,
                exc_info=True,
            )
            self._result = e
        # We finished running the function, so remove the reference to it
        # in case it's stopping garbage collection
        self._function = None
        self._args = None
        self._kwargs = None
        self._result_queue.put(None)

    def wait(self, timeout: float = None) -> None:
        # Only one person can wait on this at a time
        if self._result == self.NO_RESULT:
            self._result_queue.get(timeout)

    def ready(self) -> bool:
        """Return True if the spawned result has returned or errored"""
        return self._result != self.NO_RESULT

    def get(self, timeout: float = None) -> T:
        """Return the result or raise the error the function has produced"""
        self.wait(timeout)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class Queue:
    """Threadsafe and cothreadsafe queue with gets in calling thread"""

    def __init__(self):
        if get_thread_ident() == cothread.scheduler_thread_id:
            self._event_queue = cothread.EventQueue()
        else:
            self._event_queue = cothread.ThreadedEventQueue()

    def get(self, timeout=None):
        # In cothread's thread
        start = time.time()
        remaining_timeout = timeout
        while remaining_timeout is None or remaining_timeout >= 0:
            try:
                return self._event_queue.Wait(timeout=remaining_timeout)
            except cothread.Timedout:
                if timeout is not None:
                    remaining_timeout = start + timeout - time.time()
                    if remaining_timeout < 0:
                        raise TimeoutError("Queue().get() timed out")
        raise TimeoutError("Queue().get() given negative timeout")

    def put(self, value):
        # In cothread's thread
        self._event_queue.Signal(value)
