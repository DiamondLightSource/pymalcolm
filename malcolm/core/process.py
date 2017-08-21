from multiprocessing.pool import ThreadPool
import inspect

from malcolm.compat import OrderedDict, maybe_import_cothread, \
    get_pool_num_threads
from .context import Context
from .hook import Hook, get_hook_decorated
from .loggable import Loggable
from .spawned import Spawned
from .rlock import RLock
from .errors import WrongThreadError


# Clear spawned handles after how many spawns?
SPAWN_CLEAR_COUNT = 1000


class Process(Loggable):
    """Hosts a number of Controllers and provides spawn capabilities"""

    Init = Hook()
    """Called at start() to start all child controllers"""

    Publish = Hook()
    """Called when a new block is added

    Args:
        published (list): [mri] list of published Controller mris
    """

    Halt = Hook()
    """Called at stop() to gracefully stop all child controllers"""

    def __init__(self, name):
        super(Process, self).__init__(process=name)
        self.name = name
        self._cothread = maybe_import_cothread()
        self._controllers = OrderedDict()  # mri -> Controller
        self._published = []  # [mri] for publishable controllers
        self.started = False
        self._spawned = []
        self._spawn_count = 0
        self._thread_pool = None
        self._lock = RLock()
        self._hooked_func_names = {}
        self._hook_names = {}
        self._find_hooks()

    def _find_hooks(self):
        for name, member in inspect.getmembers(self, Hook.isinstance):
            assert member not in self._hook_names, \
                "Hook %s already in %s as %s" % (
                    self, name, self._hook_names[member])
            self._hook_names[member] = name
            self._hooked_func_names[member] = {}

    def start(self, timeout=None):
        """Start the process going

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
                process. None means forever
        """
        assert not self.started, "Process already started"
        self.started = True
        self._run_hook(self.Init, timeout=timeout)
        self._run_hook(
            self.Publish, args=(self._published,), timeout=timeout)

    def _run_hook(self, hook, controller_list=None, args=(), timeout=None):
        # Run the given hook waiting til all hooked functions are complete
        # but swallowing any errors
        if controller_list is None:
            controller_list = self._controllers.values()

        spawned = []
        for controller in controller_list:
            func_name = self._hooked_func_names[hook].get(controller, None)
            if func_name:
                func = getattr(controller, func_name)
                spawned.append(controller.spawn(func, *args))
        for s in spawned:
            s.wait(timeout)

    def stop(self, timeout=None):
        """Stop the process and wait for it to finish

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        assert self.started, "Process not started"
        # Allow every controller a chance to clean up
        self._run_hook(self.Halt, timeout=timeout)
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
        return self._call_in_right_thread(
            self._spawn, function, args, kwargs, use_cothread)

    def _call_in_right_thread(self, func, *args):
        try:
            return func(*args)
        except WrongThreadError:
            # called from outside cothread's thread, spawn it again
            return self._cothread.CallbackResult(func, *args)

    def _spawn(self, function, args, kwargs, use_cothread):
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
        self._spawn_count = 0
        self._spawned = [s for s in self._spawned if not s.ready()]

    def add_controller(self, mri, controller, publish=True, timeout=None):
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
        with self._lock:
            assert mri not in self._controllers, \
                "Controller already exists for %s" % mri
            self._controllers[mri] = controller
            for func_name, hook, _ in get_hook_decorated(controller):
                assert hook in self._hook_names, \
                    "Controller %s func %s not hooked into %s" % (
                        mri, func_name, self)
                self._hooked_func_names[hook][controller] = func_name
            if publish:
                self._published.append(mri)
        if self.started:
            self._run_hook(self.Init, [controller], timeout=timeout)
            self._run_hook(self.Publish, args=(self._published,),
                           timeout=timeout)

    def remove_controller(self, mri, timeout=None):
        """Remove a controller that is hosted by this process

        Args:
            mri (str): The malcolm resource id for the controller
            timeout (float): Maximum amount of time to wait for each spawned
                object. None means forever
        """
        self._call_in_right_thread(self._remove_controller, mri, timeout)

    def _remove_controller(self, mri, timeout):
        with self._lock:
            controller = self._controllers.pop(mri)
            for d in self._hooked_func_names.values():
                d.pop(controller, None)
            if mri in self._published:
                self._published.remove(mri)
        if self.started:
            self._run_hook(self.Publish, args=(self._published,),
                           timeout=timeout)
            self._run_hook(self.Halt, [controller], timeout=timeout)

    @property
    def mri_list(self):
        return list(self._controllers)

    def get_controller(self, mri):
        """Get controller from mri

        Args:
            mri (str): The malcolm resource id for the controller

        Returns:
            Controller: the controller
        """
        try:
            return self._controllers[mri]
        except KeyError:
            raise ValueError("No controller registered for mri %r" % mri)

    def block_view(self, mri):
        """Get a Block view from a Controller

        Args:
            mri (str): The malcolm resource id for the block

        Returns:
            Block: the block view
        """
        controller = self.get_controller(mri)
        context = Context(self)
        block = controller.make_view(context)
        return block
