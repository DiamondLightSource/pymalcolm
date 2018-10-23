import logging
import signal

from annotypes import TYPE_CHECKING
import cothread

from malcolm.compat import get_thread_ident
from .errors import TimeoutError

if TYPE_CHECKING:
    from typing import TypeVar, Callable, Any, Tuple, Dict, Union
    T = TypeVar("T")


# Make a module level logger
log = logging.getLogger(__name__)

# Re-export
sleep = cothread.Sleep
RLock = cothread.RLock


class Spawned(object):
    NO_RESULT = object()

    def __init__(self, func, args, kwargs):
        # type: (Callable[..., Any], Tuple, Dict) -> None
        self._result_queue = Queue()
        self._result = self.NO_RESULT  # type: Union[T, Exception]
        self._function = func
        self._args = args
        self._kwargs = kwargs
        cothread.Spawn(self.catching_function)

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
        self._args = None
        self._kwargs = None
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


class Queue(object):
    """Threadsafe and cothreadsafe queue with gets in calling thread"""
    INTERRUPTED = object()

    def __init__(self, user_facing=False):
        self.user_facing = user_facing
        self._event_queue = cothread.EventQueue()
        if user_facing:
            # Install a signal handler that will make sure we are the
            # thing that is interrupted
            def signal_exception(signum, frame):
                self._event_queue.Signal(self.INTERRUPTED)

            signal.signal(signal.SIGINT, signal_exception)

    def get(self, timeout=None):
        if get_thread_ident() != cothread.scheduler_thread_id:
            # Not in cothread's thread, so need to use CallbackResult
            return cothread.CallbackResult(self.get, timeout)
        else:
            # In cothread's thread
            try:
                ret = self._event_queue.Wait(timeout=timeout)
            except cothread.Timedout:
                raise TimeoutError("Queue().get() timed out")
            else:
                if ret is self.INTERRUPTED:
                    raise KeyboardInterrupt()
                else:
                    return ret

    def put(self, value):
        if cothread.scheduler_thread_id != get_thread_ident():
            # Not in cothread's thread, so need to use Callback
            cothread.Callback(self._event_queue.Signal, value)
        else:
            # In cothread's thread
            self._event_queue.Signal(value)
