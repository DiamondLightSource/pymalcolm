import time
import os

from plop.collector import Collector, FlamegraphFormatter, PlopFormatter

from malcolm.core import method_takes, Part, REQUIRED
from malcolm.modules.builtin.vmetas import BooleanMeta, StringMeta
from malcolm.compat import maybe_import_cothread


class AlwaysCollector(Collector):
    def __init__(self):
        cothread = maybe_import_cothread()
        if cothread:
            mode = "virtual"
        else:
            mode = "real"
        super(AlwaysCollector, self).__init__(0.01, mode)
        self.do_sample = False
        # Start with samples_remaining = 2
        super(AlwaysCollector, self).start(duration=0.021)

    def start(self, duration=None):
        self.do_sample = True

    def stop(self):
        self.do_sample = False
        while self.samples_remaining != 1:
            # Busy wait for sampler to finish
            pass

    def handler(self, sig, current_frame):
        if self.do_sample:
            # Ask for one more sample
            self.samples_remaining = 2
            Collector.handler(self, sig, current_frame)


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED,
    "profilesDir", StringMeta("Directory to place output results"), REQUIRED)
class ProfilingPart(Part):
    # Attribute
    running = None

    def __init__(self, params):
        super(ProfilingPart, self).__init__(params.name)
        self.params = params
        self.collector = AlwaysCollector()
        self.start_time = None
        self.start()

    def create_attributes(self):
        self.running = BooleanMeta(
            "Is profiling currently running?").create_attribute(True)
        yield "running", self.running, None

    @method_takes()
    def start(self):
        """Start the profiler going"""
        # Go forever
        self.start_time = time.time()
        self.collector.start()
        if self.running:
            self.running.set_value(True)

    @method_takes(
        "filename", StringMeta("Filename to save to"), "")
    def stop(self, params=None):
        """Stop the profiler and save to file"""
        assert self.running.value, "Not running"
        self.collector.stop()
        if params:
            filename = params.filename
        else:
            filename = ""
        if not filename:
            start_date = time.strftime(
                '%Y%m%d-%H%M%S', time.localtime(self.start_time))
            duration = time.time() - self.start_time
            filename = "%s-for-%ds" % (start_date, duration)
        file_path = os.path.join(self.params.profilesDir, filename)
        FlamegraphFormatter().store(self.collector, file_path + ".flame")
        PlopFormatter().store(self.collector, file_path + ".plop")
        self.running.set_value(False)
