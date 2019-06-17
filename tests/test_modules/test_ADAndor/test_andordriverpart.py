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
        self.mock_when_value_matches(self.child)
        # readoutTime used to be 0.002, not any more...
        self.o = AndorDriverPart(name="m", mri="mri")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def do_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 2000*3000
        file_dir = "/tmp"
        self.o.configure(
            self.context, completed_steps, steps_to_do, {}, generator=generator,
            fileDir=file_dir)

    def test_configure(self):
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True)
        # This is what the detector does when exposure and acquirePeriod are
        # both set to 0.1
        self.set_attributes(self.child, exposure=0.1, acquirePeriod=0.105)
        self.do_configure()
        # duration - readout - fudge_factor - crystal offset
        expected_exposure = pytest.approx(0.1 - 0.005 - 0.0014 - 5e-6)
        assert self.child.handled_requests.mock_calls == [
            # Checking for readout time
            call.put('exposure', 0.1),
            call.put('acquirePeriod', 0.1),
            # Setup of detector
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('exposure', expected_exposure),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6000000),
            call.put('acquirePeriod', 0.1 - 5e-6),
            call.post('start'),
            call.when_value_matches('acquiring', True, None)]
        assert self.o.exposure.value == expected_exposure

    def test_configure_frame_transfer(self):
        accumulate_period = 0.08
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True)
        # Set what we need to simulate frame transfer mode
        self.set_attributes(
            self.child, andorFrameTransferMode=True,
            andorAccumulatePeriod=accumulate_period)
        self.do_configure()
        assert self.child.handled_requests.mock_calls == [
            call.put('exposure', 0.0),
            call.put('acquirePeriod', 0.0),
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('exposure', 0.0),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6000000),
            call.put('acquirePeriod', accumulate_period),
            call.post('start'),
            call.when_value_matches('acquiring', True, None)]

