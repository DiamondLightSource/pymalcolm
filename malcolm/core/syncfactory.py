from threading import Lock
from multiprocessing.pool import ThreadPool

from malcolm.compat import Queue
from malcolm.core.loggable import Loggable


class SyncFactory(Loggable):
    """Create thread primitives and schedule tasks"""

    def __init__(self, name):
        """
        Args:
            name(str): Scheduler name e.g. "Scheduler"
        """
        super(SyncFactory, self).__init__(logger_name=name)
        self.pool = ThreadPool()

    def spawn(self, function, *args, **kwargs):
        """Runs the function in a worker thread, returning a Result object

        Args:
            function: Function to run
            args: Positional arguments to run the function with
            kwargs: Keyword arguments to run the function with

        Returns:
            object: Something you can call wait(timeout) on to see when it's
            finished executing
        """
        return self.pool.apply_async(function, args, kwargs)

    def create_queue(self):
        """Creates a new Queue object"""
        return Queue()

    def create_lock(self):
        """Creates a new simple Lock object"""
        return Lock()
