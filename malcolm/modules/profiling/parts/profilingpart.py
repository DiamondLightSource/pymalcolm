import time
import os

from plop.collector import Collector, FlamegraphFormatter, PlopFormatter

from malcolm.core import method_takes, Part, REQUIRED
from malcolm.modules.builtin.vmetas import BooleanMeta, StringMeta


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED,
    "profilesDir", StringMeta("Directory to place output results"), REQUIRED)
class ProfilingPart(Part):
    # Attribute
    running = None

    def __init__(self, params):
        super(ProfilingPart, self).__init__(params.name)
        self.params = params
        self.collector = None
        self.start_time = None

    def create_attributes(self):
        self.running = BooleanMeta(
            "Is profiling currently running?").create_attribute()
        yield "running", self.running, None

    @method_takes()
    def start(self):
        """Start the profiler going"""
        self.collector = Collector()
        # Go forever
        self.start_time = time.time()
        self.collector.start(10000000000000)
        self.running.set_value(True)

    @method_takes(
        "filename", StringMeta("Filename to save to"), "")
    def stop(self, params):
        """Stop the profiler and save to file"""
        assert self.running.value, "Not running"
        self.collector.stop()
        filename = params.filename
        if not filename:
            start_date = time.strftime(
                '%Y%m%d-%H%M%S', time.localtime(self.start_time))
            duration = time.time() - self.start_time
            filename = "%s-for-%ds" % (start_date, duration)
        file_path = os.path.join(self.params.profilesDir, filename)
        FlamegraphFormatter().store(self.collector, file_path + ".flame")
        PlopFormatter().store(self.collector, file_path + ".plop")
        self.collector = None
        self.running.set_value(False)
