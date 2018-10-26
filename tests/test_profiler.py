import ast
import logging
import time
import unittest

from malcolm.profiler import Profiler


# https://github.com/bdarnell/plop/blob/master/plop/test/collector_test.py
class ProfilerTest(unittest.TestCase):

    def filter_stacks(self, results):
        # Kind of hacky, but this is the simplest way to keep the tests
        # working after the internals of the collector changed to support
        # multiple formatters.
        stack_counts = ast.literal_eval(results)
        counts = {}
        for stack, count in stack_counts.items():
            filtered_stack = [frame[2] for frame in stack
                              if frame[0].endswith('test_profiler.py')]
            if filtered_stack:
                counts[tuple(filtered_stack)] = count

        return counts

    def check_counts(self, counts, expected):
        failed = False
        output = []
        for stack, count in expected.items():
            # every expected frame should appear in the data, but
            # the inverse is not true if the signal catches us between
            # calls.
            self.assertTrue(stack in counts)
            ratio = float(counts[stack]) / float(count)
            output.append('%s: expected %s, got %s (%s)' %
                          (stack, count, counts[stack], ratio))
            if not (0.70 <= ratio <= 1.25):
                failed = True
        if failed:
            for line in output:
                logging.warning(line)
            for key in set(counts.keys()) - set(expected.keys()):
                logging.warning(
                    'unexpected key: %s: got %s' % (key, counts[key]))
            self.fail("collected data did not meet expectations")

    def test_collector(self):
        start = time.time()

        def a(end):
            while time.time() < end: pass
            c(time.time() + 0.1)

        def b(end):
            while time.time() < end: pass
            c(time.time() + 0.1)

        def c(end):
            while time.time() < end: pass

        profiler = Profiler("/tmp")
        profiler.start(interval=0.01)
        a(time.time() + 0.1)
        b(time.time() + 0.2)
        c(time.time() + 0.3)
        end = time.time()
        profiler.stop("profiler_test.plop")
        elapsed = end - start
        self.assertTrue(0.8 < elapsed < 0.9, elapsed)

        with open("/tmp/profiler_test.plop") as f:
            results = f.read()
        counts = self.filter_stacks(results)

        expected = {
            ('a', 'test_collector'): 10,
            ('c', 'a', 'test_collector'): 10,
            ('b', 'test_collector'): 20,
            ('c', 'b', 'test_collector'): 10,
            ('c', 'test_collector'): 30,
        }
        self.check_counts(counts, expected)