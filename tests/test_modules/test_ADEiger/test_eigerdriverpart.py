from mock import call
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADEiger.blocks import eiger_driver_block
from malcolm.modules.ADEiger.parts import EigerDriverPart
from malcolm.testutil import ChildTestCase


class TestEigerDetectorDriverPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            eiger_driver_block,
            self.process,
            mri="mri",
            prefix="prefix",
            fan_prefix="FAN",
        )
        self.o = EigerDriverPart(name="m", mri="mri")
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
        steps_to_do = 2000 * 3000
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True, fanStateReady=1)
        self.o.on_configure(
            self.context,
            completed_steps,
            steps_to_do,
            {},
            generator=generator,
            fileDir="/tmp",
        )

        assert self.child.handled_requests.mock_calls == [
            call.put("arrayCallbacks", True),
            call.put("arrayCounter", 0),
            call.put("imageMode", "Multiple"),
            call.put("numImages", 6000000),
            call.put("numImagesPerSeries", 1),
            call.post("start"),
        ]
