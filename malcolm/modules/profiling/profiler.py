import time
import os

from plop.collector import Collector, FlamegraphFormatter, PlopFormatter

from malcolm.compat import maybe_import_cothread


class Profiler(Collector):
    def __init__(self, dirname, interval=0.01):
        self.dirname = dirname
        self.start_time = None
        cothread = maybe_import_cothread()
        if cothread:
            mode = "virtual"
        else:
            mode = "real"
        super(Profiler, self).__init__(interval, mode)

    def start(self, duration=None):
        # Go forever
        self.start_time = time.time()
        super(Profiler, self).start(duration=1000000)

    def stop(self, filename=None):
        super(Profiler, self).stop()
        self.store(filename)

    def store(self, filename=None):
        if not filename:
            start_date = time.strftime(
                '%Y%m%d-%H%M%S', time.localtime(self.start_time))
            duration = time.time() - self.start_time
            filename = "%s-for-%ds" % (start_date, duration)
        file_path = os.path.join(self.dirname, filename)
        FlamegraphFormatter().store(self, file_path + ".flame")
        PlopFormatter().store(self, file_path + ".plop")
