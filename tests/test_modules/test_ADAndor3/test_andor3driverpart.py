from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import call_with_params, Context, Process
from malcolm.modules.ADAndor3.parts import Andor3DriverPart
from malcolm.modules.ADAndor3.blocks import andor3_detector_driver_block
from malcolm.testutil import ChildTestCase
from numpy import float64


class TestAndor3DetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            andor3_detector_driver_block, self.process,
            mri="mri", prefix="prefix")
        choices = ["Fixed", "Continuous"]
        self.child.parts["imageMode"].attr.meta.set_choices(choices)
        self.o = call_with_params(
            Andor3DriverPart, name="m", mri="mri")
        list(self.o.create_attribute_models())
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
        # Need a known value for the readout time
        self.child.parts["readoutTime"].attr.set_value(0.002)
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        # Need to wait for the spawned mock start call to run
        self.o.start_future.result()
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('numImages', 6000000),
            call.put('shutterMode', 'Global'),
            call.put('exposure', 0.098),
            call.put('acquirePeriod', 0.1),
            call.post('start')]
