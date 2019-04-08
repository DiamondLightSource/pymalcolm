import time
import logging

from annotypes import TYPE_CHECKING, Anno, WithCallTypes, Any, Generic, \
    TypeVar, Sequence

from malcolm.compat import OrderedDict, getargspec
from .concurrency import Queue, Spawned
from .errors import AbortedError
from .loggable import Loggable
from .info import Info

if TYPE_CHECKING:
    from typing import Callable, List, Dict, Tuple, Type, Union, Optional

# Create a module level logger
log = logging.getLogger(__name__)


T = TypeVar("T")
if TYPE_CHECKING:
    Hooked = Callable[..., T]
    ArgsGen = Callable[(List[str]), List[str]]


def make_args_gen(func):
    # type: (Callable) -> ArgsGen
    call_types = getattr(func, "call_types", {})
    arg_spec = getargspec(func)
    need_args = [k for k in arg_spec.args if k != "self"]

    if need_args and not call_types:
        raise TypeError(
            "Function %s takes arguments but doesn't have call_types. Did you "
            "forget to decorate with @add_call_types?" % func)

    def args_gen(keys):
        # type: (List[str]) -> List[str]
        return call_types.keys()

    return args_gen


class Hookable(Loggable, WithCallTypes):
    """Baseclass of something that can be attached to a hook"""
    name = None  # type: str
    hooked = None  # type: Dict[Type[Hook], Tuple[Hooked, ArgsGen]]

    def register_hooked(self,
                        hooks,  # type: Union[Type[Hook], Sequence[Type[Hook]]]
                        func,  # type: Hooked
                        args_gen=None  # type: Optional[ArgsGen]
                        ):
        # type: (...) -> None
        """Register func to be run when any of the hooks are run by parent

        Args:
            hooks: A Hook class or list of Hook classes of interest
            func: The callable that should be run on that Hook
            args_gen: Optionally specify the argument names that should be
                passed to func. If not given then use func.call_types.keys
        """
        if self.hooked is None:
            self.hooked = {}
        if args_gen is None:
            args_gen = make_args_gen(func)
        if not isinstance(hooks, Sequence):
            hooks = [hooks]
        for hook_cls in hooks:
            self.hooked[hook_cls] = (func, args_gen)

    def on_hook(self, hook):
        # type: (Hook) -> None
        """Takes a hook, and optionally calls hook.run on a function"""
        try:
            func, args_gen = self.hooked[type(hook)]
        except (KeyError, TypeError):
            return
        else:
            hook(func, args_gen)


with Anno("The child that the hook is being passed to"):
    AHookable = Hookable


class Hook(Generic[T], WithCallTypes):
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

    def prepare(self):
        # type: () -> None
        """Override this if we need to prepare before running"""
        pass

    def __call__(self, func, args_gen=None):
        # type: (Callable[..., T], ArgsGen) -> None
        """Spawn the function, passing kwargs specified by func.call_types or
        keys if given"""
        assert not self.spawned, \
            "Hook has already spawned a function, cannot run another"
        self.prepare()
        if args_gen is None:
            args_gen = make_args_gen(func)
        # TODO: should we check the return types here?
        supplied = list(self._kwargs)
        demanded = args_gen(supplied)
        assert set(supplied).issuperset(demanded), \
            "Hook demanded arguments %s, but only supplied %s" % (
                demanded, supplied)
        kwargs = {k: self._kwargs[k] for k in demanded}
        self.spawned = self._spawn(self._run, func, kwargs)

    def _run(self, func, kwargs):
        # type: (Callable[..., T], Dict[str, Any]) -> None
        try:
            result = func(**kwargs)
            result = self.validate_return(result)
        except AbortedError as e:
            log.info("%s: %s has been aborted", self.child, func)
            result = e
        except Exception as e:  # pylint:disable=broad-except
            log.exception("%s: %s(**%s) raised exception %s",
                          self.child, func, kwargs, e)
            result = e
        self._queue.put((self, result))

    def stop(self):
        # type: () -> None
        """Override this if we can stop"""
        raise RuntimeError("%s cannot be stopped" % self.name)

    def validate_return(self, ret):
        # type: (T) -> None
        """Override this if the function is expected to return something to
        to validate its value"""
        assert not ret, "Expected no return, got %s" % (ret,)
        return None


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


def wait_hooks(logger, hook_queue, hook_spawned, timeout=None,
               exception_check=True):
    # type: (logging.Logger, Queue, List[Hook], float) -> Dict[str, List[Info]]
    # timeout is time to wait for spawned processes to complete on abort,
    # not time for them to run for
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
        duration = time.time() - start
        if hook_spawned:
            logger.debug(
                "%s: Child %s returned %r after %ss. Still waiting for %s",
                hook.name, hook.child.name, ret, duration,
                [h.child.name for h in hook_spawned])
        else:
            logger.debug(
                "%s: Child %s returned %r after %ss. Returning...",
                hook.name, hook.child.name, ret, duration)

        if isinstance(ret, Exception) and exception_check:
            if not isinstance(ret, AbortedError):
                # If AbortedError, all tasks have already been stopped.
                # Got an error, so stop and wait all hook runners
                for h in hook_spawned:
                    h.stop()
            # Wait for them to finish
            for h in hook_spawned:
                h.spawned.wait(timeout)
            raise ret
        else:
            return_dict[hook.child.name] = ret

    return return_dict
