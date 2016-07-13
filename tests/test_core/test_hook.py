import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, patch

from malcolm.core.hook import Hook


class DummyController(object):

    Configuring = Hook()
    Running = Hook()


class DummyPart1(object):

    @DummyController.Configuring
    def do_thing(self):
        pass

    @DummyController.Running
    def do_the_other_thing(self):
        pass


class DummyPart2(object):

    @DummyController.Configuring
    def do_all_the_things(self):
        pass


class TestHook(unittest.TestCase):

    def test_decorator(self):

        self.assertEqual(type(DummyPart1().do_thing.Hook), Hook)

    def setUp(self):
        block_mock = MagicMock()
        block_mock.name = "TestBlock"
        self.c = DummyController()
        self.c.block = block_mock

    def test_run_sets_logger_name(self):
        self.c.parts = []
        self.c.process = MagicMock()
        part = DummyPart1()

        part.do_thing.Hook.run(self.c)

        self.assertEqual(part.do_thing.Hook._logger.name, "TestBlock.Configuring")

    @patch('malcolm.core.hook.Task')
    def test_run_makes_correct_calls(self, task_mock):
        process_mock = MagicMock()
        queue_mock = MagicMock()
        spawn_mock = MagicMock()
        spawned_mock = MagicMock()
        spawn_mock.return_value = spawned_mock
        process_mock.create_queue.return_value = queue_mock
        process_mock.spawn = spawn_mock
        process_mock.q.get.return_value = (task_mock.return_value, MagicMock())
        self.c.process = process_mock
        part1 = DummyPart1()
        part2 = DummyPart2()
        self.c.parts = [part1, part2]

        response = part1.do_thing.Hook.run(self.c)

        task_calls = [call[0][0] for call in task_mock.call_args_list]
        self.assertEqual(task_calls, [self.c.process]*2)
        spawn_calls = [call[0] for call in spawn_mock.call_args_list]
        self.assertEqual(spawn_calls[0],
                         (Hook._run_func, queue_mock, part1.do_thing,
                          task_mock.return_value))
        self.assertEqual(spawn_calls[1],
                         (Hook._run_func, queue_mock, part2.do_all_the_things,
                          task_mock.return_value))

        self.assertEqual(2, process_mock.q.get.call_count)

        self.assertIsNone(response)

    @patch('malcolm.core.hook.Task')
    def test_run_stops_after_exception_raised(self, task_mock):
        process_mock = MagicMock()
        queue_mock = MagicMock()
        spawn_mock = MagicMock()
        spawned_mock = MagicMock()
        spawn_mock.return_value = spawned_mock
        process_mock.spawn = spawn_mock
        process_mock.create_queue.return_value = queue_mock
        process_mock.q.get.return_value = (task_mock.return_value, Exception())
        self.c.process = process_mock
        part1 = DummyPart1()
        part2 = DummyPart2()
        self.c.parts = [part1, part2]

        with self.assertRaises(Exception):
            part1.do_thing.Hook.run(self.c)

        task_mock.return_value.stop.assert_called_once_with()
        self.assertEqual(2, spawned_mock.wait.call_count)

    def test_run_func(self):
        queue_mock = MagicMock()
        func_mock = MagicMock()
        func_mock.return_value = 1
        task_mock = MagicMock()

        Hook._run_func(queue_mock, func_mock, task_mock)

        func_mock.assert_called_once_with(task_mock)
        queue_mock.put.assert_called_once_with((task_mock, 1))

    def test_run_func_raises(self):
        queue_mock = MagicMock()
        func_mock = MagicMock()
        exception = Exception("Error occurred")
        func_mock.side_effect = exception
        task_mock = MagicMock()

        Hook._run_func(queue_mock, func_mock, task_mock)

        func_mock.assert_called_once_with(task_mock)
        queue_mock.put.assert_called_once_with((task_mock, exception))

if __name__ == "__main__":
    unittest.main(verbosity=2)
