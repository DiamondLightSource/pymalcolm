import unittest

from annotypes import add_call_types, Anno
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Part, Process, Context, APartName
from malcolm.modules.builtin.hooks import AContext
from malcolm.modules.scanning.hooks import RunHook
from malcolm.modules.scanning.parts import RunnableChildPart
from malcolm.modules.scanning.controllers import RunnableController


with Anno("How long to wait"):
    AWait = float


class WaitingPart(Part):
    def __init__(self, name, wait):
        # type: (APartName, AWait) -> None
        super(WaitingPart, self).__init__(name)
        self.wait = wait
        self.register_hooked(RunHook, self.run)

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        context.sleep(self.wait)


class TestRunnableChildPart(unittest.TestCase):

    def setUp(self):
        self.p = Process('process1')
        self.context = Context(self.p)

        # Make a fast child
        c1 = RunnableController(mri="fast", config_dir="/tmp")
        c1.add_part(WaitingPart("p", 0.01))
        self.p.add_controller(c1)

        # And a slow one
        c2 = RunnableController(mri="slow", config_dir="/tmp")
        c2.add_part(WaitingPart("p", 1.0))
        self.p.add_controller(c2)

        # And a top level one
        c3 = RunnableController(mri="top", config_dir="/tmp")
        c3.add_part(
            RunnableChildPart(name="FAST", mri="fast", initial_visibility=True))
        c3.add_part(
            RunnableChildPart(name="SLOW", mri="slow", initial_visibility=True))
        self.p.add_controller(c3)

        # Some blocks to interface to them
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
        self.b.configure(generator=self.make_generator(), axesToMove=())
        assert self.b.completedSteps.value == 0
        assert self.b.totalSteps.value == 6
        assert self.b.configuredSteps.value == 1
        # Do one step
        self.b.run()
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





