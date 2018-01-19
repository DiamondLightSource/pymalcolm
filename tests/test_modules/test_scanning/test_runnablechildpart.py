import unittest

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import call_with_params, Part, Process, Context
from malcolm.modules.scanning.parts import RunnableChildPart
from malcolm.modules.scanning.controllers import RunnableController


class WaitingPart(Part):
    def __init__(self, name, wait):
        super(WaitingPart, self).__init__(name)
        self.wait = wait

    @RunnableController.Run
    def run(self, context, update_completed_steps):
        context.sleep(self.wait)


class TestRunnableChildPart(unittest.TestCase):

    def setUp(self):
        self.p = Process('process1')
        self.context = Context(self.p)

        # Make a fast child
        c1 = call_with_params(RunnableController, self.p,
                              [WaitingPart("p", 0.01)],
                              mri="fast", config_dir="/tmp")
        self.p.add_controller("fast", c1)

        # And a slow one
        c2 = call_with_params(RunnableController,  self.p,
                              [WaitingPart("p", 1.0)],
                              mri="slow", config_dir="/tmp")
        self.p.add_controller("slow", c2)

        # And a top level one
        p1 = call_with_params(RunnableChildPart, name="FAST", mri="fast")
        p2 = call_with_params(RunnableChildPart, name="SLOW", mri="slow")
        c3 = call_with_params(RunnableController, self.p, [p1, p2],
                              mri="top", config_dir="/tmp")
        self.p.add_controller("top", c3)
        self.b = self.context.block_view("top")
        self.bf = self.context.block_view("fast")
        self.bs = self.context.block_view("slow")

        # start the process off
        self.p.start()

    def tearDown(self):
        self.p.stop(timeout=1)

    def make_generator(self):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        return compound

    def test_not_paused_when_resume(self):
        # Set it up to do 6 steps
        self.b.configure(generator=self.make_generator())
        assert self.b.completedSteps.value == 0
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 1
        # Do one step
        self.b.__call__()
        assert self.b.completedSteps.value == 1
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 2
        # Now do a second step but pause before the second one is done
        f = self.b.run_async()
        self.context.sleep(0.2)
        assert self.b.state.value == "Running"
        assert self.bf.state.value == "Armed"
        assert self.bs.state.value == "Running"
        self.b.pause()
        assert self.b.state.value == "Paused"
        assert self.bf.state.value == "Armed"
        assert self.bs.state.value == "Paused"
        assert self.b.completedSteps.value == 1
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 2
        self.b.resume()
        self.context.wait_all_futures(f)
        assert self.b.completedSteps.value == 2
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 3





