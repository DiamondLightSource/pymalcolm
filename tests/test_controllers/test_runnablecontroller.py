import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, call
import time

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core import Process, Part, Task, Map, AbortedError, ResponseError
from malcolm.core.syncfactory import SyncFactory
from malcolm.controllers.runnablecontroller import RunnableController
from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.blocks.demo import Ticker


class TestRunnableController(unittest.TestCase):

    def checkState(self, state, child=True, parent=True):
        if child:
            self.assertEqual(self.b_child.state, state)
        if parent:
            self.assertEqual(self.b.state, state)

    def checkSteps(self, configured, completed, total):
        self.assertEqual(self.b.configuredSteps, configured)
        self.assertEqual(self.b.completedSteps, completed)
        self.assertEqual(self.b.totalSteps, total)
        self.assertEqual(self.b_child.configuredSteps, configured)
        self.assertEqual(self.b_child.completedSteps, completed)
        self.assertEqual(self.b_child.totalSteps, total)

    def setUp(self):
        self.maxDiff = 5000

        self.p = Process('process1', SyncFactory('threading'))

        # Make a ticker block to act as our child
        params = Ticker.MethodMeta.prepare_input_map(
            mri="childBlock",
            configDir="/tmp"
        )
        self.b_child = Ticker(self.p, params)[-1]

        # Make an empty part for our parent
        params = Part.MethodMeta.prepare_input_map(name='part1')
        part1 = Part(self.p, params)

        # Make a RunnableChildPart to control the ticker
        params = RunnableChildPart.MethodMeta.prepare_input_map(
            mri='childBlock', name='part2')
        part2 = RunnableChildPart(self.p, params)

        # create a root block for the RunnableController block to reside in
        params = RunnableController.MethodMeta.prepare_input_map(
            mri='mainBlock', configDir="/tmp")
        self.c = RunnableController(self.p, [part1, part2], params)
        self.b = self.c.block
        self.sm = self.c.stateMachine

        # start the process off
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
        self.assertEqual(self.b['completedSteps'].meta.typeid,
                         'malcolm:core/NumberMeta:1.0')
        self.assertEqual(self.b['configuredSteps'].meta.typeid,
                         'malcolm:core/NumberMeta:1.0')
        self.assertEqual(self.b['axesToMove'].meta.typeid,
                         'malcolm:core/StringArrayMeta:1.0')

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

    def test_edit(self):
        self.b.edit()
        self.checkState(self.sm.EDITABLE, child=False)

    def test_reset(self):
        self.b.disable()
        self.checkState(self.sm.DISABLED)
        self.b.reset()
        self.checkState(self.sm.IDLE)

    def test_set_axes_to_move(self):
        self.c.set_axes_to_move(['y'])
        self.assertEqual(self.c.axes_to_move.value, ('y',))

    def test_validate(self):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        actual = self.b.validate(generator=compound, axesToMove=['x'])
        self.assertEqual(actual["generator"], compound)
        self.assertEqual(actual["axesToMove"], ('x',))

    def prepare_half_run(self, duration=0.01, exception=0):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration)
        self.b.configure(
            generator=compound, axesToMove=['x'], exceptionStep=exception)

    def test_configure_run(self):
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.sm.READY)

        self.b.run()
        self.checkState(self.sm.READY)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.sm.READY)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.sm.IDLE)

    def test_abort(self):
        self.prepare_half_run()
        self.b.run()
        self.b.abort()
        self.checkState(self.sm.ABORTED)

    def test_pause_seek_resume(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)
        self.b.run()
        self.checkState(self.sm.READY)
        self.checkSteps(4, 2, 6)
        self.b.pause(completedSteps=1)
        self.checkState(self.sm.READY)
        self.checkSteps(2, 1, 6)
        self.b.run()
        self.checkSteps(4, 2, 6)
        self.b.completedSteps = 5
        self.checkSteps(6, 5, 6)
        self.b.run()
        self.checkState(self.sm.IDLE)

    def test_resume_in_run(self):
        self.prepare_half_run(duration=0.5)
        w = self.p.spawn(self.b.run)
        time.sleep(0.85)
        self.b.pause()
        self.checkState(self.sm.PAUSED)
        self.checkSteps(2, 1, 6)
        self.b.resume()
        # return to PRERUN should continue original run to completion and
        # READY state
        then = time.time()
        w.wait()
        self.assertAlmostEqual(time.time() - then, 0.5, delta=0.4)
        self.checkState(self.sm.READY)

    def test_run_exception(self):
        self.prepare_half_run(exception=1)
        with self.assertRaises(ResponseError):
            self.b.run()
        self.checkState(self.sm.FAULT)

    def test_run_stop(self):
        self.prepare_half_run(duration=0.5)
        w = self.p.spawn(self.b.run)
        time.sleep(0.5)
        self.b.abort()
        with self.assertRaises(AbortedError):
            w.get()
        self.checkState(self.sm.ABORTED)

if __name__ == "__main__":
    unittest.main(verbosity=2)
