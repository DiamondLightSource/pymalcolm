import time
import logging

from annotypes import TYPE_CHECKING, Anno, WithCallTypes, Any

from malcolm.compat import OrderedDict
from .errors import AbortedError
from .loggable import Loggable
from .queue import Queue
from .spawned import Spawned
from .info import Info

if TYPE_CHECKING:
    from typing import Callable, List, Dict, Tuple, Optional
    Hooked = Callable[..., Optional[List[Info]]]


# Create a module level logger
log = logging.getLogger(__name__)


class Hookable(Loggable, WithCallTypes):
    name = None  # type: str

    def on_hook(self, hook):
        # type: (Hook) -> None
        """Takes a hook, and optionally calls hook.run on a function"""
        return


with Anno("The child that the hook is being passed to"):
    AHookable = Hookable


class Hook(WithCallTypes):
    """Something that children can register with to be called"""
    def __init__(self, child, **kwargs):
        # type: (AHookable, **Any) -> None
        self.child = child
        self._kwargs = kwargs
        self._queue = None  # type: Queue
        self._spawn = None  # type: Callable[..., Spawned]
        self.spawned = None  # type: Spawned

    @property
    def name(self):
        return type(self).__name__

    def set_spawn(self, spawn):
        # type: (Callable[..., Spawned]) -> Hook
        self._spawn = spawn
        return self

    def set_queue(self, queue):
        # type: (Queue) -> Hook
        self._queue = queue
        return self

    def run(self, func, *args):
        # type: (Hooked) -> None
        call_types = getattr(func, "call_types", {})  # type: Dict[str, Anno]
        kwargs = {k: self._kwargs[k] for k in call_types}
        self.spawned = self._spawn(self._run, func, args, kwargs)

    def _run(self, func, args, kwargs):
        # type: (Hooked, Tuple, Dict[str, Any]) -> None
        try:
            infos = func(*args, **kwargs)
            result = self.validate_infos(infos)
        except AbortedError as e:
            log.info("%s: %s has been aborted", self.child, func)
            result = e
        except Exception as e:  # pylint:disable=broad-except
            log.exception("%s: %s(*%s, **%s) raised exception %s",
                          self.child, func, args, kwargs, e)
            result = e
        self._queue.put((self, result))

    def stop(self):
        """Override this if we can stop"""
        # type: () -> None
        raise RuntimeError("%s cannot be stopped" % self.name)

    def validate_infos(self, infos=None):
        # type: (Optional[List[Info]]) -> List[Info]
        """Override this to validate the return from the function"""
        if infos is None:
            return []
        assert isinstance(infos, list), "Expected [Info], got %s" % (infos,)
        for info in infos:
            assert isinstance(info, Info), "Expected Info, got %s" % (infos,)
        return infos


def start_hooks(hooks):
    # type: (List[Hook]) -> Tuple[Queue, List[Hook]]
    # This queue will hold (part, result) tuples
    hook_queue = Queue()
    hook_spawned = []
    # now start them off
    for hook in hooks:
        hook.set_queue(hook_queue)
        hook.child.on_hook(hook)
        if hook.spawned:
            hook_spawned.append(hook)
    return hook_queue, hook_spawned


def wait_hooks(hook_queue, hook_spawned, timeout=None):
    # type: (Queue, List[Hook], float) -> Dict[str, List[Info]]
    # Wait for them all to finish
    return_dict = OrderedDict()
    for hook in hook_spawned:
        return_dict[hook.child.name] = None
    start = time.time()
    hook_spawned = set(hook_spawned)
    while hook_spawned:
        hook, ret = hook_queue.get()  # type: Tuple[Hook, Any]
        hook_spawned.remove(hook)
        # Wait for the process to terminate
        hook.spawned.wait(timeout)
        return_dict[hook.child.name] = ret
        duration = time.time() - start
        if hook_spawned:
            log.debug(
                "%s: Child %s returned %r after %ss. Still waiting for %s",
                hook.name, hook.child.name, ret, duration,
                [h.child.name for h in hook_spawned])
        else:
            log.debug(
                "%s: Child %s returned %r after %ss. Returning...",
                hook.name, hook.child.name, ret, duration)

        if isinstance(ret, Exception):
            if not isinstance(ret, AbortedError):
                # If AbortedError, all tasks have already been stopped.
                # Got an error, so stop and wait all hook runners
                for h in hook_spawned:
                    h.stop()
            # Wait for them to finish
            for h in hook_spawned:
                h.spawned.wait(timeout)
            raise ret

    return return_dict
