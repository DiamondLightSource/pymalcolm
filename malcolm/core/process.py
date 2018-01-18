from multiprocessing.pool import ThreadPool

from annotypes import Anno, Array, TYPE_CHECKING

from malcolm.compat import OrderedDict, maybe_import_cothread, \
    get_pool_num_threads
from .context import Context
from .controller import Controller
from .errors import WrongThreadError
from .hook import Hook, start_hooks, AHookable
from .loggable import Loggable
from .rlock import RLock
from .spawned import Spawned
from .views import Block

if TYPE_CHECKING:
    from typing import List, Callable, Dict, Any, Tuple, TypeVar
    T = TypeVar("T")


# Clear spawned handles after how many spawns?
SPAWN_CLEAR_COUNT = 1000


class ProcessStartHook(Hook[None]):
    """Called at start() to start all child controllers"""


with Anno("The list of currently published Controller mris"):
    APublished = Array[str]


class ProcessPublishHook(Hook[None]):
    """Called when a new block is added"""
    def __init__(self, child, published):
        # type: (AHookable, APublished) -> None
        super(ProcessPublishHook, self).__init__(child)
        self.published = APublished(published)


class ProcessStopHook(Hook[None]):
    """Called at stop() to gracefully stop all child controllers"""


class Process(Loggable):
    """Hosts a number of Controllers and provides spawn capabilities"""

    def __init__(self, name):
        # type: (str) -> None
        self.set_logger(name=name)
        self.name = name
        self._cothread = maybe_import_cothread()
        self._controllers = OrderedDict()  # mri -> Controller
        self._published = []  # [mri] for publishable controllers
        self.started = False
        self._spawned = []
        self._spawn_count = 0
        self._thread_pool = None
        self._lock = RLock()

    def start(self, timeout=None):
        """Start the process going

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
                process. None means forever
        """
        assert not self.started, "Process already started"
        self.started = True
        self._run_hook(ProcessStartHook, timeout=timeout)
        self._run_hook(ProcessPublishHook, timeout=timeout,
                       published=self._published)

    def _run_hook(self, hook, controller_list=None, timeout=None, **kwargs):
        # Run the given hook waiting til all hooked functions are complete
        # but swallowing any errors
        if controller_list is None:
            controller_list = self._controllers.values()
        hooks = [hook(controller, **kwargs).set_spawn(controller.spawn)
                 for controller in controller_list]
        hook_queue, hook_spawned = start_hooks(hooks)
        while hook_spawned:
            hook, ret = hook_queue.get()
            hook_spawned.remove(hook)
            # Wait for the process to terminate
            hook.spawned.wait(timeout)

    def stop(self, timeout=None):
        """Stop the process and wait for it to finish

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        assert self.started, "Process not started"
        # Allow every controller a chance to clean up
        self._run_hook(ProcessStopHook, timeout=timeout)
        for s in self._spawned:
            self.log.debug("Waiting for %s", s._function)
            s.wait(timeout=timeout)
        self._spawned = []
        self._controllers = OrderedDict()
        self._published = []
        self.started = False
        if self._thread_pool:
            self._thread_pool.close()
            self._thread_pool.join()
            self._thread_pool = None

    def spawn(self, function, args, kwargs, use_cothread):
        # type: (Callable[..., Any], Tuple, Dict, bool) -> Spawned
        """Runs the function in a worker thread, returning a Result object

        Args:
            function: Function to run
            args: Positional arguments to run the function with
            kwargs: Keyword arguments to run the function with
            use_cothread (bool): Whether to try and run this as a cothread

        Returns:
            Spawned: Something you can call wait(timeout) on to see when it's
                finished executing
        """
        ret = self._call_in_right_thread(
            self._spawn, function, args, kwargs, use_cothread)
        return ret

    def _call_in_right_thread(self, func, *args):
        # type: (Callable[..., T], *Any) -> T
        try:
            return func(*args)
        except WrongThreadError:
            # called from outside cothread's thread, spawn it again
            return self._cothread.CallbackResult(func, *args)

    def _spawn(self, function, args, kwargs, use_cothread):
        # type: (Callable[..., Any], Tuple, Dict, bool) -> Spawned
        with self._lock:
            assert self.started, "Can't spawn before process started"
            if self._thread_pool is None:
                if not self._cothread or not use_cothread:
                    self._thread_pool = ThreadPool(get_pool_num_threads())
            spawned = Spawned(
                function, args, kwargs, use_cothread, self._thread_pool)
            self._spawned.append(spawned)
            self._spawn_count += 1
            # Filter out things that are ready to avoid memory leaks
            if self._spawn_count > SPAWN_CLEAR_COUNT:
                self._clear_spawn_list()
        return spawned

    def _clear_spawn_list(self):
        # type: () -> None
        self._spawn_count = 0
        self._spawned = [s for s in self._spawned if not s.ready()]

    def add_controller(self, mri, controller, publish=True, timeout=None):
        # type: (str, Controller, bool, float) -> None
        """Add a controller to be hosted by this process

        Args:
            mri (str): The malcolm resource id for the controller
            controller (Controller): Its controller
            publish (bool): Whether to notify other controllers about its
                existence
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        self._call_in_right_thread(
            self._add_controller, mri, controller, publish, timeout)

    def _add_controller(self, mri, controller, publish, timeout):
        # type: (str, Controller, bool, float) -> None
        with self._lock:
            assert mri not in self._controllers, \
                "Controller already exists for %s" % mri
            self._controllers[mri] = controller
            controller.setup(self)
            if publish:
                self._published.append(mri)
        if self.started:
            self._run_hook(ProcessStartHook, [controller], timeout=timeout)
            self._run_hook(ProcessPublishHook, args=(self._published,),
                           timeout=timeout)

    def remove_controller(self, mri, timeout=None):
        # type: (str, float) -> None
        """Remove a controller that is hosted by this process

        Args:
            mri (str): The malcolm resource id for the controller
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        self._call_in_right_thread(self._remove_controller, mri, timeout)

    def _remove_controller(self, mri, timeout):
        # type: (str, float) -> None
        with self._lock:
            controller = self._controllers.pop(mri)
            if mri in self._published:
                self._published.remove(mri)
        if self.started:
            self._run_hook(ProcessPublishHook, timeout=timeout,
                           published=self._published)
            self._run_hook(ProcessStopHook, [controller], timeout=timeout)

    @property
    def mri_list(self):
        # type: () -> List[str]
        return list(self._controllers)

    def get_controller(self, mri):
        # type: (str) -> Controller
        """Get controller which can make Block views for this mri"""
        try:
            return self._controllers[mri]
        except KeyError:
            raise ValueError("No controller registered for mri %r" % mri)

    def block_view(self, mri):
        # type: (str) -> Block
        """Get a Block view from a Controller with given mri"""
        controller = self.get_controller(mri)
        context = Context(self)
        block = controller.make_view(context)
        return block
