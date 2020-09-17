from typing import Any, Callable, List, Sequence, Set, TypeVar, Union

from annotypes import Anno, Array

from malcolm.compat import OrderedDict

from .concurrency import Spawned
from .controller import DEFAULT_TIMEOUT, Controller
from .errors import TimeoutError
from .hook import AHookable, Hook, start_hooks, wait_hooks
from .info import Info
from .loggable import Loggable

T = TypeVar("T")


# Clear spawned handles after how many spawns?
SPAWN_CLEAR_COUNT = 1000

# States for how far in start procedure we've got
STOPPED = 0
STARTING = 1
STARTED = 2
STOPPING = 3


with Anno("The list of currently published Controller mris"):
    APublished = Union[Array[str]]


class UnpublishedInfo(Info):
    def __init__(self, mri: str) -> None:
        self.mri = mri


class ProcessPublishHook(Hook):
    """Called when a new block is added"""

    def __init__(self, child: AHookable, published: APublished) -> None:
        super().__init__(child, published=published)


with Anno("Each of these reports that the controller should not be published"):
    AUnpublishedInfos = Union[Array[UnpublishedInfo]]
UUnpublishedInfos = Union[
    AUnpublishedInfos, Sequence[UnpublishedInfo], UnpublishedInfo, None
]


class ProcessStartHook(Hook):
    """Called at start() to start all child controllers"""

    def validate_return(self, ret: UUnpublishedInfos) -> AUnpublishedInfos:
        """Check that all returns are UnpublishedInfo objects indicating
        that the controller shouldn't be published via any server comms"""
        return AUnpublishedInfos(ret)


class ProcessStopHook(Hook):
    """Called at stop() to gracefully stop all child controllers"""


class Process(Loggable):
    """Hosts a number of Controllers and provides spawn capabilities"""

    def __init__(self, name: str = "Process") -> None:
        self.set_logger(process_name=name)
        self.name = name
        self._controllers = OrderedDict()  # mri -> Controller
        self._unpublished: Set[str] = set()  # [mri] for unpublishable controllers
        self.state = STOPPED
        self._spawned: List[Spawned] = []
        self._spawn_count = 0

    def start(self, timeout=DEFAULT_TIMEOUT):
        """Start the process going

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
                process. None means forever
        """
        assert self.state == STOPPED, "Process already started"
        self.state = STARTING
        should_publish = self._start_controllers(self._controllers.values(), timeout)
        if should_publish:
            self._publish_controllers(timeout)
        self.state = STARTED

    def _start_controllers(
        self, controller_list: List[Controller], timeout: float = None
    ) -> bool:
        # Start just the given controller_list
        infos = self._run_hook(ProcessStartHook, controller_list, timeout=timeout)
        info: UnpublishedInfo
        new_unpublished = set()
        for info in UnpublishedInfo.filter_values(infos):
            new_unpublished.add(info.mri)
        self._unpublished |= new_unpublished
        if len(controller_list) > len(new_unpublished):
            return True
        else:
            return False

    def _publish_controllers(self, timeout):
        tree = OrderedDict()
        is_child = set()

        def add_controller(controller: Controller) -> OrderedDict:
            children = OrderedDict()
            tree[controller.mri] = children
            for part in controller.parts.values():
                part_mri = getattr(part, "mri", None)
                is_child.add(part_mri)
                if part_mri in tree:
                    children[part_mri] = tree[part_mri]
                elif part_mri in self._controllers:
                    children[part_mri] = add_controller(self._controllers[part_mri])
            return tree[controller.mri]

        for c in self._controllers.values():
            if c.mri not in is_child:
                add_controller(c)

        published = []

        def walk(d, not_at_this_level=()):
            to_do = []
            for k, v in d.items():
                if k in not_at_this_level:
                    continue
                if k not in published and k not in self._unpublished:
                    published.append(k)
                if v:
                    to_do.append(v)
            for v in to_do:
                walk(v)

        walk(tree, not_at_this_level=is_child)

        self._run_hook(ProcessPublishHook, timeout=timeout, published=published)

    def _run_hook(self, hook, controller_list=None, timeout=None, **kwargs):
        # Run the given hook waiting til all hooked functions are complete
        # but swallowing any errors
        if controller_list is None:
            controller_list = self._controllers.values()
        hooks = [
            hook(controller, **kwargs).set_spawn(self.spawn)
            for controller in controller_list
        ]
        hook_queue, hook_spawned = start_hooks(hooks)
        infos = wait_hooks(
            self.log, hook_queue, hook_spawned, timeout, exception_check=False
        )
        problems = [mri for mri, e in infos.items() if isinstance(e, Exception)]
        if problems:
            self.log.warning("Problem running %s on %s", hook.__name__, problems)
        return infos

    def stop(self, timeout=DEFAULT_TIMEOUT):
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
            if not s.ready():
                self.log.debug(
                    "Waiting for %s *%s **%s", s._function, s._args, s._kwargs
                )
            try:
                s.wait(timeout=timeout)
            except TimeoutError:
                self.log.warning(
                    "Timeout waiting for %s *%s **%s", s._function, s._args, s._kwargs
                )
                raise
        self._spawned = []
        self._controllers = OrderedDict()
        self._unpublished = set()
        self.state = STOPPED
        self.log.debug("Done process.stop()")

    def spawn(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Spawned:
        """Runs the function in a worker thread, returning a Result object

        Args:
            function: Function to run
            args: Positional arguments to run the function with
            kwargs: Keyword arguments to run the function with

        Returns:
            Spawned: Something you can call wait(timeout) on to see when it's
                finished executing
        """
        assert self.state != STOPPED, "Can't spawn when process stopped"
        spawned = Spawned(function, args, kwargs)
        self._spawned.append(spawned)
        self._spawn_count += 1
        # Filter out things that are ready to avoid memory leaks
        if self._spawn_count > SPAWN_CLEAR_COUNT:
            self._clear_spawn_list()
        return spawned

    def _clear_spawn_list(self) -> None:
        self._spawn_count = 0
        self._spawned = [s for s in self._spawned if not s.ready()]

    def add_controllers(
        self, controllers: List[Controller], timeout: float = None
    ) -> None:
        """Add many controllers to be hosted by this process

        Args:
            controllers (List[Controller]): List of its controller
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        for controller in controllers:
            assert controller.mri not in self._controllers, (
                "Controller already exists for %s" % controller.mri
            )
            self._controllers[controller.mri] = controller
            controller.setup(self)
        if self.state:
            should_publish = self._start_controllers(controllers, timeout)
            if self.state == STARTED and should_publish:
                self._publish_controllers(timeout)

    def add_controller(self, controller: Controller, timeout: float = None) -> None:
        """Add a controller to be hosted by this process

        Args:
            controller (Controller): Its controller
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        self.add_controllers([controller], timeout=timeout)

    @property
    def mri_list(self) -> List[str]:
        return list(self._controllers)

    def get_controller(self, mri: str) -> Controller:
        """Get controller which can make Block views for this mri"""
        try:
            return self._controllers[mri]
        except KeyError:
            raise ValueError("No controller registered for mri '%s'" % mri)

    def block_view(self, mri: str) -> Any:
        """Get a Block view from a Controller with given mri"""
        controller = self.get_controller(mri)
        block = controller.block_view()
        return block
