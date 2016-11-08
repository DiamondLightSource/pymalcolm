import collections
import sys
import signal


class ProfilingSampler(object):
    def __init__(self, interval=0.1):
        self.stack_counts = collections.defaultdict(int)
        self.interval = interval

    def _sample(self, _, _2):
        for frame in sys._current_frames().values():
            stack = []
            while frame is not None:
                formatted_frame = '{}({})'.format(
                    frame.f_code.co_name, frame.f_globals.get('__name__'))
                stack.append(formatted_frame)
                frame = frame.f_back

            formatted_stack = ';'.join(reversed(stack))
            self.stack_counts[formatted_stack] += 1
        signal.setitimer(signal.ITIMER_VIRTUAL, self.interval, 0)

    def start(self):
        signal.signal(signal.SIGVTALRM, self._sample)
        signal.setitimer(signal.ITIMER_VIRTUAL, self.interval, 0)
