import collections
import sys
import signal


class ProfilingSampler(object):
    def __init__(self, interval=0.1):
        self.stack_counts = collections.defaultdict(int)
        self.interval = interval
        self._started = False
        signal.signal(signal.SIGPROF, self._sample)

    def _format_stack(self, frame):
        stack = []
        while frame is not None:
            if frame.f_code.co_name == "wait":
                return
            stack.append(frame)
            frame = frame.f_back
        formatted = []
        for frame in reversed(stack):
            formatted_frame = '%s(%s)' % (
                frame.f_code.co_name, frame.f_globals.get('__name__'))
            formatted.append(formatted_frame)
        return ';'.join(formatted)

    def _sample(self, _, _2):
        for frame in sys._current_frames().values():
            formatted_stack = self._format_stack(frame)
            if formatted_stack:
                self.stack_counts[formatted_stack] += 1
        if self._started:
            signal.setitimer(signal.ITIMER_PROF, self.interval, 0)

    def start(self):
        self._started = True
        signal.setitimer(signal.ITIMER_PROF, self.interval, 0)

    def stop(self):
        self._started = False

    def most_common_stack_frames(self):
        for v, k in sorted((v, k) for k, v in self.stack_counts.items()):
            print "%06d: %s" % (v, "\n        ".join(k.split(";")))
