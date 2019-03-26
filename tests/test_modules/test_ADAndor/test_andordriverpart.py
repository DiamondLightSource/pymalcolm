import pytest
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
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 2000*3000
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True)
        # This is what the detector does when exposure and acquirePeriod are
        # both set to 0.1
        self.set_attributes(self.child, exposure=0.1, acquirePeriod=0.105)
        self.o.configure(
            self.context, completed_steps, steps_to_do, {}, generator=generator, fileDir="/tmp")
        assert self.child.handled_requests.mock_calls == [
            call.put('exposure', 0.1),
            call.put('acquirePeriod', 0.1),
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            # duration - readout - fudge_factor - crystal offset
            call.put('exposure', pytest.approx(0.1 - 0.005 - 0.0014 - 5e-6)),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6000000),
            call.put('acquirePeriod', 0.1 - 5e-6),
            call.post('start'),
            call.when_values_matches('acquiring', True, None, 10.0, None)]
