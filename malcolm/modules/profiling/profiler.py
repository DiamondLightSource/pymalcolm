import time
import os

from plop.collector import Collector, FlamegraphFormatter, PlopFormatter

from malcolm.compat import get_pool_num_threads


class Profiler(Collector):
    def __init__(self, dirname, mode="prof", interval=0.001):
        self.dirname = dirname
        self.start_time = None
        self.started = False
        num_threads = get_pool_num_threads() + 1
        super(Profiler, self).__init__(interval * num_threads, mode)

    def start(self, duration=None):
        # Go forever
        self.start_time = time.time()
        self.started = True
        super(Profiler, self).start(duration=1000000)

    def stop(self, filename=None, reset=True):
        super(Profiler, self).stop()
        self.started = False
        self.store(filename)
        if reset:
            self.reset()

    def store(self, filename=None):
        if not filename:
            start_date = time.strftime(
                '%Y%m%d-%H%M%S', time.localtime(self.start_time))
            duration = time.time() - self.start_time
            filename = "%s-for-%ds" % (start_date, duration)
        file_path = os.path.join(self.dirname, filename)
        FlamegraphFormatter().store(self, file_path + ".flame")
        PlopFormatter().store(self, file_path + ".plop")
