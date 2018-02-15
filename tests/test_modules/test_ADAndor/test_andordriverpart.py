from mock import call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import Context, Process
from malcolm.modules.ADAndor.parts import AndorDriverPart
from malcolm.modules.ADAndor.blocks import andor_driver_block
from malcolm.testutil import ChildTestCase


class TestAndorDetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            andor_driver_block, self.process,
            mri="mri", prefix="prefix")
        # readoutTime used to be 0.002, not any more...
        self.o = AndorDriverPart(name="m", mri="mri")
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 2000*3000
        self.o.configure(
            self.context, completed_steps, steps_to_do, generator)
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('exposure', 0.087000000000000008),
            call.put('imageMode', 'Fixed'),
            call.put('numImages', 6000000),
            call.put('acquirePeriod', 0.1),
            call.post('start')]
