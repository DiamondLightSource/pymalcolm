import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, call
from time import sleep

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core import method_writeable_in, method_takes, \
        DefaultStateMachine, Block, Controller, REQUIRED
from malcolm.core.vmetas import BooleanMeta
from malcolm.core import Process, Part, RunnableStateMachine, Task
from malcolm.core.syncfactory import SyncFactory
from malcolm.controllers.runnablecontroller import RunnableController
from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart

class TestRunnableController(unittest.TestCase):

    def checkState(self, state, child=True, parent=True):
        if child:
            self.assertEqual(self.c_child.state.value, state)
        if parent:
            self.assertEqual(self.c.state.value, state)

    def checkSteps(self, configured, completed, total):
        self.assertEqual(self.c.configured_steps.value, configured)
        self.assertEqual(self.c.completed_steps.value, completed)
        self.assertEqual(self.c.total_steps.value, total)
        self.assertEqual(self.c_child.configured_steps.value, configured)
        self.assertEqual(self.c_child.completed_steps.value, completed)
        self.assertEqual(self.c_child.total_steps.value, total)

    def setUp(self):
        self.maxDiff = 5000

        self.p = Process('process1', SyncFactory('threading'))

        # create a child RunnableController block
        params = RunnableController.MethodMeta.prepare_input_map(
            mri='childBlock')
        self.c_child = RunnableController(self.p, {}, params)
        self.b_child = self.c_child.block

        self.sm = self.c_child.stateMachine

        params = Part.MethodMeta.prepare_input_map(name='part1')
        part1 = Part(self.p, params)
        params = {'mri': 'childBlock', 'name': 'part2'}
        params = RunnableChildPart.MethodMeta.prepare_input_map(**params)
        part2 = RunnableChildPart(self.p, params)

        # create a root block for the RunnableController block to reside in
        parts = [part1, part2]
        params = {'mri': 'mainBlock'}
        params = RunnableController.MethodMeta.prepare_input_map(**params)
        self.c = RunnableController(self.p, parts, params)
        self.b = self.c.block

        # check that do_initial_reset works asynchronously
        self.checkState(self.sm.DISABLED)
        self.p.start()

        # wait until block is Ready
        task = Task("block_ready_task", self.p)
        task.when_matches(self.b["state"], self.sm.IDLE, timeout=1)

        self.checkState(self.sm.IDLE)

    def tearDown(self):
        self.p.stop()

    def test_init(self):
        # the following block attributes should be created by a call to
        # set_attributes via _set_block_children in __init__
        self.assertEqual(self.b['totalSteps'].meta.typeid,
                         'malcolm:core/NumberMeta:1.0')
        self.assertEqual(self.b['layout'].meta.typeid,
                         'malcolm:core/TableMeta:1.0')
        self.assertEqual(self.b['completedSteps'].meta.typeid,
                         'malcolm:core/NumberMeta:1.0')
        self.assertEqual(self.b['configuredSteps'].meta.typeid,
                         'malcolm:core/NumberMeta:1.0')
        self.assertEqual(self.b['axesToMove'].meta.typeid,
                         'malcolm:core/StringArrayMeta:1.0')
        self.assertEqual(self.b['layoutName'].meta.typeid,
                         'malcolm:core/StringMeta:1.0')

        # the following hooks should be created via _find_hooks in __init__
        self.assertEqual(self.c.hook_names, {
            self.c.Reset: "Reset",
            self.c.Disable: "Disable",
            self.c.ReportOutports: "ReportOutports",
            self.c.Layout: "Layout",
            self.c.Load: "Load",
            self.c.Save: "Save",
            self.c.Validate: "Validate",
            self.c.ReportStatus: "ReportStatus",
            self.c.Configure: "Configure",
            self.c.PostConfigure: "PostConfigure",
            self.c.Run: "Run",
            self.c.PostRunReady: "PostRunReady",
            self.c.PostRunIdle: "PostRunIdle",
            self.c.Seek: "Seek",
            self.c.Pause: "Pause",
            self.c.Resume: "Resume",
            self.c.Abort: "Abort",
        })

        # check instantiation of object tree via logger names
        self.assertEqual(self.c._logger.name,
                         'RunnableController(mainBlock)')
        self.assertEqual(self.c.parts['part1']._logger.name,
                         'RunnableController(mainBlock).part1')
        self.assertEqual(self.c.parts['part2']._logger.name,
                         'RunnableController(mainBlock).part2')
        self.assertEqual(self.c_child._logger.name,
                         'RunnableController(childBlock)')

    def test_edit(self):
        self.c.edit()
        self.checkState(self.sm.EDITABLE, child=False)

    def test_reset(self):
        self.c.disable()
        self.checkState(self.sm.DISABLED)
        self.c.reset()
        self.checkState(self.sm.IDLE)

    def test_set_axes_to_move(self):
        self.c.set_axes_to_move(['axisOne'])
        self.assertEqual(self.c.axes_to_move.value, ['axisOne'])

    def test_validate(self):
        # todo validate currently broken
        return
        line1 = LineGenerator('AxisOne', 'mm', 0, 2, 3)
        line2 = LineGenerator('AxisTwo', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        params = {'generator': compound, 'axesToMove': ['AxisTwo']}
        params = \
            RunnableController.validate.MethodMeta.prepare_input_map(**params)
        self.c.configure(params)
        self.c.validate(params)

        # self.c.do_validate = lambda p, r: None
        # self.c.validate(None)

    def prepare_half_run(self):
        line1 = LineGenerator('AxisOne', 'mm', 0, 2, 3)
        line2 = LineGenerator('AxisTwo', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        params = {'generator': compound, 'axesToMove': ['AxisTwo']}
        params = \
            RunnableController.configure.MethodMeta.prepare_input_map(**params)
        self.c.configure(params)

    def test_configure_run(self):
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.sm.READY)

        self.c.run()
        self.checkState(self.sm.READY)
        self.checkSteps(4, 2, 6)

        self.c.run()
        self.checkState(self.sm.READY)
        self.checkSteps(6, 4, 6)

        self.c.run()
        self.checkState(self.sm.IDLE)

    def test_abort(self):
        self.prepare_half_run()
        self.c.run()
        self.c.abort()
        self.checkState(self.sm.ABORTED)

    def test_pause_seek_resume(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)
        self.b.run()
        self.checkState(self.sm.READY)
        self.checkSteps(4, 2, 6)

        params = {'completedSteps': 1}
        params = RunnableController.seek.MethodMeta.prepare_input_map(**params)
        self.c.seek(params)
        self.checkState(self.sm.READY)
        self.checkSteps(2, 1, 6)
        self.c.run()
        self.checkSteps(4, 2, 6)
        params = {'completedSteps': 5}
        params = RunnableController.seek.MethodMeta.prepare_input_map(**params)
        self.c.seek(params)
        self.checkSteps(6, 5, 6)
        self.c.run()
        self.checkState(self.sm.IDLE)

    def dummy_run_hook(self, hook, part_tasks, *args, **params):
        hook_queue, task_part_names = self.c_child.start_hook(
            hook, part_tasks, *args, **params)
        if hook == self.c.Run:
            # restore normal run hook function
            self.c_child.run_hook = self.child_hook
            self.p.spawn(self.c.pause())
        return_dict = self.c_child.wait_hook(hook_queue, task_part_names)
        return return_dict

    def test_resume_in_run(self):
        # TODO: this not yet working
        return

        class MyPart(Part):
            @RunnableController.Run
            def wait_a_bit(self, task, params):
                task.sleep(10)

        params = Part.MethodMeta.prepare_input_map(name='part1')
        self.c.parts["part1"] = MyPart(self.p, params)

        self.prepare_half_run()
        self.child_hook = self.c_child.run_hook
        self.c_child.run_hook = self.dummy_run_hook
        self.p.spawn(self.c.run)
        retry = 0
        while  retry < 20 and self.c.state.value != self.sm.PAUSED:
            sleep(.1)
            retry += 1
        self.checkState(self.sm.PAUSED)
        self.c.transition(self.sm.PRERUN, 'un-pausing')
        # return to PRERUN should continue original run to completion and
        # READY state
        retry = 0
        while  retry < 20 and self.c_child.state.value != self.sm.READY:
            sleep(.1)
            retry += 1
        self.checkState(self.sm.READY)

    def test_configure_exception(self):
        self.c_child.run_hook = Mock(side_effect=Exception("test exception"))
        with self.assertRaises(Exception):
            self.prepare_half_run()
        self.checkState(self.sm.FAULT)

    def test_configure_exception_parent(self):
        self.c.run_hook = Mock(side_effect=Exception("test exception"))
        with self.assertRaises(Exception):
            self.prepare_half_run()
        self.checkState(self.sm.FAULT, child=False)
        self.checkState(self.sm.IDLE, parent=False)

    def test_run_exception(self):
        self.prepare_half_run()
        self.c_child.run_hook = Mock(side_effect=Exception("test exception"))
        with self.assertRaises(Exception):
            self.c.run()
        self.checkState(self.sm.FAULT)

    def test_run_stop(self):
        self.prepare_half_run()
        self.c_child.run_hook = Mock(side_effect=StopIteration("test exception"))
        with self.assertRaises(ValueError):
            self.c_child.run()
        self.checkState(self.sm.FAULT, parent=False)

    def test_abort_exception(self):
        self.prepare_half_run()
        self.c.run()
        self.c_child.run_hook = Mock(side_effect=Exception("test exception"))
        with self.assertRaises(Exception):
            self.c.abort()
        self.checkState(self.sm.FAULT)

    def test_pause_exception(self):
        self.prepare_half_run()
        self.c.run()
        with self.assertRaises(Exception):
            self.c.pause()
        # the exception here is 'pause not writable' so does not affect child
        # state - it does however code cover the exception handler in pause
        self.checkState(self.sm.FAULT, child=False)

    def test_seek_exception(self):
        self.prepare_half_run()
        self.c.run()
        self.c_child.run_hook = Mock(side_effect=Exception("test exception"))
        with self.assertRaises(Exception):
            params = {'completedSteps': 4}
            params = RunnableController.seek.MethodMeta.prepare_input_map(**params)
            self.c.seek(params)
        self.checkState(self.sm.FAULT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
