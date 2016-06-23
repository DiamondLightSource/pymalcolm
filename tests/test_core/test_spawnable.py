import os
import sys
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
from mock import Mock, call

from malcolm.core.spawnable import Spawnable


class DummySpawnable(Spawnable):
    def __init__(self):
        super(DummySpawnable, self).__init__()
        self.started = False
        self.stopped = False
        self.q = Mock()
        self.add_spawn_function(self.start_func_1, self.stop_func_1)
        self.add_spawn_function(self.start_func_2,
                                self.make_default_stop_func(self.q))

    def start_func_1(self):
        self.started = True

    def start_func_2(self):
        self.second_started = True

    def stop_func_1(self):
        self.stopped = True

class TestSpawnable(unittest.TestCase):

    def test_start_stop(self):
        s = Spawnable()
        process = Mock()
        f1 = Mock()
        f1_stop = Mock()
        f2 = Mock()
        s.add_spawn_function(f1, f1_stop)
        s.add_spawn_function(f2)

        s.start(process)

        spawned_args = process.spawn.call_args_list
        self.assertEqual([call(f1), call(f2)], spawned_args)

        s.stop()
        f1_stop.assert_called_once_with()

    def test_wait_called(self):
        s = Spawnable()
        process = Mock()
        f1 = Mock()
        s.add_spawn_function(f1)
        s.start(process)
        s.stop()
        timeout = Mock()
        s.wait(timeout)

        process.spawn.return_value.wait.assert_called_once_with(
            timeout=timeout)

    def test_provided_stop_func(self):
        s = Spawnable()
        q = Mock()
        f_stop = s.make_default_stop_func(q)

        f_stop()
        q.put.assert_called_once_with(Spawnable.STOP)

    def test_start_stop_order(self):
        s = Spawnable()
        f1, f1_stop = Mock(), Mock()
        f2, f2_stop = Mock(), Mock()
        f3 = Mock()
        f4, f4_stop = Mock(), Mock()

        stop_parent = Mock()
        stop_parent.attach_mock(f1_stop, "f1_stop")
        stop_parent.attach_mock(f2_stop, "f2_stop")
        stop_parent.attach_mock(f4_stop, "f4_stop")

        s.add_spawn_function(f1, f1_stop)
        s.add_spawn_function(f2, f2_stop)
        s.add_spawn_function(f3)
        s.add_spawn_function(f4, f4_stop)

        process = Mock()
        s.start(process)
        self.assertEquals([call(f1), call(f2), call(f3), call(f4)],
                          process.spawn.call_args_list)
        s.stop()
        self.assertEquals([call.f4_stop(), call.f2_stop(), call.f1_stop()],
                          stop_parent.method_calls)

    def test_start_default_values(self):
        s = Spawnable()
        s.process = Mock()
        f = Mock()
        s.add_spawn_function(f)

        s.start()
        s.process.spawn.assert_called_once_with(f)

class TestSpawnableClass(unittest.TestCase):
    def test_dummy_start_stop(self):
        s = DummySpawnable()
        process = Mock()
        process.spawn = Mock(side_effect=lambda x: x())
        s.start(process)
        self.assertEqual([call(s.start_func_1), call(s.start_func_2)],
                         process.spawn.call_args_list)
        self.assertTrue(s.started)
        s.stop()
        self.assertTrue(s.stopped)

if __name__ == "__main__":
    unittest.main(verbosity=2)
