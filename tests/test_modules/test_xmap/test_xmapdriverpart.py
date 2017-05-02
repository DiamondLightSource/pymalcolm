from mock import MagicMock, ANY, call

from malcolm.core import Context, call_with_params, Process
from malcolm.modules.xmap.parts import XmapDriverPart
from malcolm.modules.xmap.blocks import xmap_detector_driver_block
from malcolm.testutil import ChildTestCase


class TestXmap3DetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            xmap_detector_driver_block, self.process,
            mri="mri", prefix="prefix")
        self.o = call_with_params(XmapDriverPart, name="m", mri="mri")
        list(self.o.create_attributes())
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_configure(self):
        params = MagicMock()
        completed_steps = 1234
        steps_to_do = 456
        part_info = ANY
        self.o.post_configure = MagicMock()
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        # Need to wait for the spawned mock start call to run
        self.o.start_future.result()
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', completed_steps),
            call.put('autoPixelsPerBuffer', 'Manual'),
            call.put('binsInSpectrum', 2048),
            call.put('collectMode', 'MCA mapping'),
            call.put('dxp1MaxEnergy', 4.096),
            call.put('dxp2MaxEnergy', 4.096),
            call.put('dxp3MaxEnergy', 4.096),
            call.put('dxp4MaxEnergy', 4.096),
            call.put('ignoreGate', 'No'),
            call.put('inputLogicPolarity', 'Normal'),
            call.put('pixelAdvanceMode', 'Gate'),
            call.put('pixelsPerBuffer', 1),
            call.put('pixelsPerRun', steps_to_do),
            call.put('presetMode', 'No preset'),
            call.post('start')]
