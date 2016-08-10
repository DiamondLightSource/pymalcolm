class Spawnable(object):
    """Mixin for starting and stopping spawned functions.
    Functions called by self.start are spawned under a provided process
    (or self.process if one is not provided).
    Functions called by self.stop are called synchronously, in reverse order.
    """
    # Sentinel object to stop spawned loops
    STOP = object()

    _spawned = None
    _spawn_functions = None

    def _initialize(self):
        if self._spawn_functions is None:
            self._spawn_functions = []
        if self._spawned is None:
            self._spawned = []

    def start(self, process=None):
        """Spawn registered functions

        Args:
            process: Process to use for spawning (default self.process)
        """
        if process is None:
            process = self.process
        self._initialize()
        for (func, _) in self._spawn_functions:
            self._spawned.append(process.spawn(func))

    def stop(self):
        """Call registered stop functions"""

        self._initialize()
        for (_, stop_func) in reversed(self._spawn_functions):
            if stop_func is not None:
                stop_func()

    def wait(self, timeout=None):
        self._initialize()
        for spawned in self._spawned:
            spawned.wait(timeout=timeout)
        self._spawned = []

    def add_spawn_function(self, func, stop_func=None):
        """Register functions to be triggered by self.start and self.stop

        Args:
            func: function to be spawned
            stop_func: function to halt the spawned function (default None)
        """
        self._initialize()
        self._spawn_functions.append((func, stop_func))

    def make_default_stop_func(self, q):
        """Convenience function for creating a default stop function that puts
        a Spawnable.STOP object onto the provided queue

        Args:
            q (queue): queue to put the stop sentinel on
        """
        def stop_func():
            q.put(Spawnable.STOP)
        return stop_func
