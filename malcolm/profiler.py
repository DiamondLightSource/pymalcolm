import collections
import signal
import sys
import time
import os

from enum import Enum

from malcolm.compat import get_profiler_dir, get_thread_ident


class ProfilerMode(Enum):
    # Profile modes for use in the interrupt func
    PROF = (signal.ITIMER_PROF, signal.SIGPROF)
    VIRTUAL = (signal.ITIMER_VIRTUAL, signal.SIGVTALRM)
    REAL = (signal.ITIMER_REAL, signal.SIGALRM)


# A combination of plop.Collector and plot.Formatter
class Profiler(object):
    def __init__(self, dirname=None, mode=ProfilerMode.PROF):
        # type: (str, ProfilerMode) -> None
        if not dirname:
            dirname = get_profiler_dir()
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        self.dirname = dirname
        self.mode = mode
        self.start_time = None
        self.running = False
        self.stopping = False
        self.stacks = []
        sig = mode.value[1]
        signal.signal(sig, self.handler)
        signal.siginterrupt(sig, False)

    def handler(self, sig, current_frame):
        if self.stopping:
            # Told to stop, cancel timer and return
            timer = self.mode.value[0]
            signal.setitimer(timer, 0, 0)
            self.running = False
        else:
            current_tid = get_thread_ident()
            for tid, frame in sys._current_frames().items():
                if tid == current_tid:
                    frame = current_frame
                frames = []
                while frame is not None:
                    code = frame.f_code
                    frames.append(
                        (code.co_filename, code.co_firstlineno, code.co_name))
                    frame = frame.f_back
                self.stacks.append(frames)

    def start(self, interval=0.001):
        assert not self.running, "Profiler already started"
        self.start_time = time.time()
        self.stopping = False
        self.running = True
        self.stacks = []
        timer = self.mode.value[0]
        signal.setitimer(timer, interval, interval)

    def stop(self, filename=None):
        assert self.running, "Profiler already stopped"
        self.stopping = True
        while self.running:
            pass  # need busy wait; ITIMER_PROF doesn't proceed while sleeping
        # If not given a filename, calculate one
        if not filename:
            start_date = time.strftime(
                '%Y%m%d-%H%M%S', time.localtime(self.start_time))
            duration = time.time() - self.start_time
            filename = "%s-for-%ds.plop" % (start_date, duration)
        # Format to be compatible with plop viewer
        stack_counts = collections.Counter(
            tuple(frames) for frames in self.stacks)
        max_stacks = 50
        stack_counts = dict(sorted(stack_counts.items(),
                                   key=lambda kv: -kv[1])[:max_stacks])
        with open(os.path.join(self.dirname, filename), "w") as f:
            f.write(repr(stack_counts))
        return filename
