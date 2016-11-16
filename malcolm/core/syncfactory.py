from threading import Lock
from multiprocessing.pool import ThreadPool

from malcolm.compat import queue
from malcolm.core.loggable import Loggable


class SyncFactory(Loggable):
    """Create thread primitives and schedule tasks"""

    def __init__(self, name):
        """
        Args:
            name(str): Logger name e.g. "Sync"
        """
        self.set_logger_name(name)
        # Need at least as many threads as concurrent blocks...
        self.pool = ThreadPool(128)

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
        return InterruptableQueue()

    def create_lock(self):
        """Creates a new simple Lock object"""
        return Lock()

    def __del__(self):
        """When we get garbage collected, clean up the threads we created"""
        self.pool.close()
        self.pool.join()


class InterruptableQueue(queue.Queue):
    # horrible horrible
    # http://stackoverflow.com/a/212975
    def get(self, block=True, timeout=None):
        if timeout is None:
            while True:
                try:
                    return queue.Queue.get(self, block=block, timeout=1000)
                except queue.Empty:
                    pass
        else:
            return queue.Queue.get(self, block=block, timeout=timeout)
