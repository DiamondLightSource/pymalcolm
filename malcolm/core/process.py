from multiprocessing.pool import ThreadPool

from annotypes import Anno, Array, TYPE_CHECKING, Union, Sequence

from malcolm.compat import OrderedDict, maybe_import_cothread, \
    get_pool_num_threads, str_
from .context import Context
from .controller import Controller
from .errors import WrongThreadError
from .hook import Hook, start_hooks, AHookable, wait_hooks
from .info import Info
from .loggable import Loggable
from .rlock import RLock
from .spawned import Spawned
from .views import Block

if TYPE_CHECKING:
    from typing import List, Callable, Dict, Any, Tuple, TypeVar

    T = TypeVar("T")


# Clear spawned handles after how many spawns?
SPAWN_CLEAR_COUNT = 1000

# States for how far in start procedure we've got
STOPPED = 0
STARTING = 1
STARTED = 2
STOPPING = 3


with Anno("The list of currently published Controller mris"):
    APublished = Array[str]


class UnpublishedInfo(Info):
    def __init__(self, mri):
        # type: (str) -> None
        self.mri = mri


class ProcessPublishHook(Hook[None]):
    """Called when a new block is added"""
    def __init__(self, child, published):
        # type: (AHookable, APublished) -> None
        super(ProcessPublishHook, self).__init__(child, published=published)


with Anno("Each of these reports that the controller should not be published"):
    AUnpublishedInfos = Array[UnpublishedInfo]
UUnpublishedInfos = Union[AUnpublishedInfos, Sequence[UnpublishedInfo],
                          UnpublishedInfo, None]


class ProcessStartHook(Hook[None]):
    """Called at start() to start all child controllers"""

    def validate_return(self, ret):
        # type: (UUnpublishedInfos) -> AUnpublishedInfos
        """Check that all returns are UnpublishedInfo objects indicating
        that the controller shouldn't be published via any server comms"""
        return AUnpublishedInfos(ret)


class ProcessStopHook(Hook[None]):
    """Called at stop() to gracefully stop all child controllers"""


class Process(Loggable):
    """Hosts a number of Controllers and provides spawn capabilities"""

    def __init__(self, name):
        # type: (str_) -> None
        self.set_logger(process_name=name)
        self.name = name
        self._cothread = maybe_import_cothread()
        self._controllers = OrderedDict()  # mri -> Controller
        self._unpublished = set()  # [mri] for unpublishable controllers
        self.state = STOPPED
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
        assert self.state == STOPPED, "Process already started"
        self.state = STARTING
        should_publish = self._start_controllers(
            self._controllers.values(), timeout)
        if should_publish:
            self._publish_controllers(timeout)
        self.state = STARTED

    def _start_controllers(self, controller_list, timeout=None):
        # type: (List[Controller], float) -> bool
        # Start just the given controller_list
        infos = self._run_hook(ProcessStartHook, controller_list,
                               timeout=timeout, user_facing=True)
        new_unpublished = set(
            info.mri for info in UnpublishedInfo.filter_values(infos))
        with self._lock:
            self._unpublished |= new_unpublished
        if len(controller_list) > len(new_unpublished):
            return True
        else:
            return False

    def _publish_controllers(self, timeout):
        # New controllers to publish
        published = [mri for mri in self._controllers
                     if mri not in self._unpublished]
        self._run_hook(ProcessPublishHook,
                       timeout=timeout, published=published)

    def _run_hook(self, hook, controller_list=None, timeout=None,
                  user_facing=False, **kwargs):
        # Run the given hook waiting til all hooked functions are complete
        # but swallowing any errors
        if controller_list is None:
            controller_list = self._controllers.values()
        hooks = [hook(controller, **kwargs).set_spawn(controller.spawn)
                 for controller in controller_list]
        hook_queue, hook_spawned = start_hooks(hooks, user_facing)
        return wait_hooks(
            self.log, hook_queue, hook_spawned, timeout, exception_check=False)

    def stop(self, timeout=None):
        """Stop the process and wait for it to finish

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        assert self.state == STARTED, "Process not started"
        self.state = STOPPING
        # Allow every controller a chance to clean up
        self._run_hook(ProcessStopHook, timeout=timeout)
        for s in self._spawned:
            self.log.debug(
                "Waiting for %s *%s **%s", s._function, s._args, s._kwargs)
            s.wait(timeout=timeout)
        self._spawned = []
        self._controllers = OrderedDict()
        self._unpublished = set()
        self.state = STOPPED
        if self._thread_pool:
            self.log.debug("Waiting for thread pool")
            self._thread_pool.close()
            self._thread_pool.join()
            self._thread_pool = None
        self.log.debug("Done process.stop()")

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
            assert self.state != STOPPED, "Can't spawn when process stopped"
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

    def add_controller(self, controller, timeout=None):
        # type: (Controller, float) -> None
        """Add a controller to be hosted by this process

        Args:
            controller (Controller): Its controller
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        self._call_in_right_thread(
            self._add_controller, controller, timeout)

    def _add_controller(self, controller, timeout):
        # type: (Controller, float) -> None
        with self._lock:
            assert controller.mri not in self._controllers, \
                "Controller already exists for %s" % controller.mri
            self._controllers[controller.mri] = controller
            controller.setup(self)
        if self.state:
            should_publish = self._start_controllers([controller], timeout)
            if self.state == STARTED and should_publish:
                self._publish_controllers(timeout)

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
            raise ValueError("No controller registered for mri '%s'" % mri)

    def block_view(self, mri):
        # type: (str) -> Block
        """Get a Block view from a Controller with given mri"""
        controller = self.get_controller(mri)
        context = Context(self)
        block = controller.make_view(context)
        return block
