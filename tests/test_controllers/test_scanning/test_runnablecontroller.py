import unittest
import time
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

# module imports
from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import Process, Part, call_with_params, \
    Context, ResponseError
from malcolm.parts.scanning.runnablechildpart import RunnableChildPart
from malcolm.blocks.demo import ticker_block
from malcolm.compat import OrderedDict
from malcolm.controllers.scanning.runnablecontroller import \
    RunnableController, RunnableStates


class TestRunnableStates(unittest.TestCase):

    def setUp(self):
        self.o = RunnableStates()

    def test_init(self):
        expected = OrderedDict()
        expected['Resetting'] = {"Ready", "Fault", "Disabling"}
        expected['Ready'] = {"Configuring", "Aborting", 'Editing', "Fault",
                             "Disabling", "Loading"}
        expected['Editing'] = {'Disabling', 'Editable', 'Fault'}
        expected['Editable'] = {'Fault', 'Saving', 'Disabling', 'Reverting'}
        expected['Saving'] = {'Fault', 'Ready', 'Disabling'}
        expected['Reverting'] = {'Fault', 'Ready', 'Disabling'}
        expected['Loading'] = {'Disabling', 'Fault', 'Ready'}
        expected['Configuring'] = {"Armed", "Aborting", "Fault", "Disabling"}
        expected['Armed'] = {"Seeking", "Resetting", "Aborting", "Running",
                             "Fault", "Disabling"}
        expected['Running'] = {"PostRun", "Seeking", "Aborting", "Fault",
                               "Disabling"}
        expected['PostRun'] = {"Ready", "Armed", "Aborting", "Fault",
                               "Disabling"}
        expected['Paused'] = {"Seeking", "Running", "Aborting", "Fault",
                              "Disabling"}
        expected['Seeking'] = {"Armed", "Paused", "Aborting", "Fault",
                               "Disabling"}
        expected['Aborting'] = {"Aborted", "Fault", "Disabling"}
        expected['Aborted'] = {"Resetting", "Fault", "Disabling"}
        expected['Fault'] = {"Resetting", "Disabling"}
        expected['Disabling'] = {"Disabled", "Fault"}
        expected['Disabled'] = {"Resetting"}
        assert self.o._allowed == expected


class TestRunnableController(unittest.TestCase):
    def setUp(self):
        self.p = Process('process1')
        self.context = Context("c", self.p)

        # Make a ticker_block block to act as our child
        self.c_child = call_with_params(
            ticker_block, self.p, mri="childBlock", configDir="/tmp")
        self.b_child = self.context.block_view("childBlock")

        # Make an empty part for our parent
        part1 = Part("part1")

        # Make a RunnableChildPart to control the ticker_block
        part2 = call_with_params(
            RunnableChildPart, mri='childBlock', name='part2')

        # create a root block for the RunnableController block to reside in
        self.c = call_with_params(RunnableController, self.p, [part1, part2],
                                  mri='mainBlock', configDir="/tmp",
                                  axesToMove=["x"])
        self.p.add_controller('mainBlock', self.c)
        self.b = self.context.block_view("mainBlock")
        self.ss = self.c.stateSet

        # start the process off
        self.checkState(self.ss.DISABLED)
        self.p.start()
        self.checkState(self.ss.READY)

    def tearDown(self):
        self.p.stop()

    def checkState(self, state, child=True, parent=True):
        if child:
            assert self.c_child.state.value == state
        if parent:
            assert self.c.state.value == state

    def checkSteps(self, configured, completed, total):
        assert self.b.configuredSteps.value == configured
        assert self.b.completedSteps.value == completed
        assert self.b.totalSteps.value == total
        assert self.b_child.configuredSteps.value == configured
        assert self.b_child.completedSteps.value == completed
        assert self.b_child.totalSteps.value == total

    def test_init(self):
        assert self.c.completed_steps.value == 0
        assert self.c.configured_steps.value == 0
        assert self.c.total_steps.value == 0
        assert self.c.axes_to_move.value == ("x",)
        assert list(self.b.configure.takes.elements) == \
               ["generator", "axesToMove", "exceptionStep"]

    def test_edit(self):
        self.c.edit()
        self.checkState(self.ss.EDITABLE, child=False)

    def test_reset(self):
        self.c.disable()
        self.checkState(self.ss.DISABLED)
        self.c.reset()
        self.checkState(self.ss.READY)

    def test_set_axes_to_move(self):
        self.c.set_axes_to_move(['y'])
        self.assertEqual(self.c.axes_to_move.value, ('y',))

    def test_validate(self):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        actual = self.b.validate(generator=compound, axesToMove=['x'])
        assert actual["generator"].to_dict() == compound.to_dict()
        assert actual["axesToMove"] == ('x',)

    def prepare_half_run(self, duration=0.01, exception=0):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], duration)
        self.b.configure(
            generator=compound, axesToMove=['x'], exceptionStep=exception)

    def test_configure_run(self):
        self.prepare_half_run()
        self.checkSteps(2, 0, 6)
        self.checkState(self.ss.ARMED)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)

        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(6, 4, 6)

        self.b.run()
        self.checkState(self.ss.READY)

    def test_abort(self):
        self.prepare_half_run()
        self.b.run()
        self.b.abort()
        self.checkState(self.ss.ABORTED)

    def test_pause_seek_resume(self):
        self.prepare_half_run()
        self.checkSteps(configured=2, completed=0, total=6)
        self.b.run()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        self.b.pause(completedSteps=1)
        self.checkState(self.ss.ARMED)
        self.checkSteps(2, 1, 6)
        self.b.run()
        self.checkSteps(4, 2, 6)
        self.b.completedSteps.value = 5
        self.checkSteps(6, 5, 6)
        self.b.run()
        self.checkState(self.ss.READY)

    def test_resume_in_run(self):
        self.prepare_half_run(duration=0.5)
        f = self.b.run_async()
        self.context.sleep(0.55)
        self.b.pause()
        self.checkState(self.ss.PAUSED)
        self.checkSteps(2, 1, 6)
        self.b.resume()
        # Parent should be running, child won't have got request yet
        then = time.time()
        self.checkState(self.ss.RUNNING, child=False)
        self.context.wait_all_futures(f)
        now = time.time()
        self.checkState(self.ss.ARMED)
        self.checkSteps(4, 2, 6)
        self.assertAlmostEqual(now - then, 0.5, delta=0.3)

    def test_run_exception(self):
        self.prepare_half_run(exception=1)
        with self.assertRaises(ResponseError):
            self.b.run()
        self.checkState(self.ss.FAULT)

    def test_run_stop(self):
        self.prepare_half_run(duration=0.1)
        f = self.b.run_async()
        self.context.sleep(0.1)
        self.b.abort()
        with self.assertRaises(ResponseError):
            f.result()
        self.checkState(self.ss.ABORTED)

if __name__ == "__main__":
    unittest.main(verbosity=2)
