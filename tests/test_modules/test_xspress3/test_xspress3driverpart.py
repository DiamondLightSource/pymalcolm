from mock import call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import Context, Process
from malcolm.modules.ADCore.infos import ExposureDeadtimeInfo
from malcolm.modules.xspress3.parts import Xspress3DriverPart
from malcolm.modules.xspress3.blocks import xspress3_driver_block
from malcolm.testutil import ChildTestCase


class TestXspress3DetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            xspress3_driver_block, self.process,
            mri="mri", prefix="prefix")
        self.o = Xspress3DriverPart(name="m", mri="mri")
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        part_info = dict(anything=[ExposureDeadtimeInfo(5e-7, 1000)])
        steps_to_do = 2000*3000
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, generator)
        # Wait for the start_future so the post gets through to our child
        # even on non-cothread systems
        self.o.actions.start_future.result(timeout=1)
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('exposure', 0.1 - 5e-7 - 0.0001),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6000000),
            call.put('pointsPerRow', 15000),
            call.put('triggerMode', 'Hardware'),
            call.put('acquirePeriod', 0.1),
            call.post('start')]
