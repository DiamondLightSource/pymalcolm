from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import call_with_params, Context, Process
from malcolm.modules.xspress3.parts import Xspress3DriverPart
from malcolm.modules.xspress3.blocks import xspress3_detector_driver_block
from malcolm.testutil import ChildTestCase


class TestXspress3DetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            xspress3_detector_driver_block, self.process,
            mri="mri", prefix="prefix")
        self.o = call_with_params(
            Xspress3DriverPart, readoutTime=0.002, name="m", mri="mri")
        list(self.o.create_attributes())
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_configure(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        params.generator.prepare()
        completed_steps = 0
        steps_to_do = 2000*3000
        part_info = ANY
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        # Need to wait for the spawned mock start call to run
        self.o.start_future.result()
        assert self.child.handled_requests.mock_calls == [
            call.put('pointsPerRow', 15000),
            call.put('triggerMode', 'Hardware'),
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6000000),
            call.put('exposure', 0.098),
            call.post('start')]
