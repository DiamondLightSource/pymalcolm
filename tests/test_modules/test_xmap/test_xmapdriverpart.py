from mock import MagicMock, call

from malcolm.core import Context, Process
from malcolm.modules.xmap.parts import XmapDriverPart
from malcolm.modules.xmap.blocks import xmap_driver_block
from malcolm.testutil import ChildTestCase


class TestXmap3DetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            xmap_driver_block, self.process,
            mri="mri", prefix="prefix")
        self.o = XmapDriverPart(name="m", mri="mri")
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_configure(self):
        completed_steps = 0
        steps_to_do = 456
        self.o.post_configure = MagicMock()
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True)
        self.o.configure(
            self.context, completed_steps, steps_to_do, {}, MagicMock())
        # Wait for the start_future so the post gets through to our child
        # even on non-cothread systems
        self.o.actions.start_future.result(timeout=1)
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
            call.post('start'),
            call.when_values_matches('acquiring', True, None, 10.0, None)]
