import unittest
from mock import MagicMock, ANY, call

from malcolm.core import Context, call_with_params
from malcolm.modules.xmap.parts import XmapDriverPart


class TestXmap3DetectorDriverPart(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=Context)
        self.o = call_with_params(
            XmapDriverPart, readoutTime=0.002, name="m", mri="mri")

    def test_configure(self):
        params = MagicMock()
        completed_steps = MagicMock()
        steps_to_do = MagicMock()
        part_info = ANY
        self.o.post_configure = MagicMock()
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        assert self.context.mock_calls == [
            call.unsubscribe_all(),
            call.block_view("mri"),
            call.block_view().put_attribute_values(dict(
                collectMode="MCA mapping",
                pixelAdvanceMode="Gate",
                presetMode="No preset",
                ignoreGate="No",
                pixelsPerRun=steps_to_do,
                autoPixelsPerBuffer="Manual",
                pixelsPerBuffer=1,
                binsInSpectrum=2048,
                dxp1MaxEnergy=4.096,
                dxp2MaxEnergy=4.096,
                dxp3MaxEnergy=4.096,
                dxp4MaxEnergy=4.096,
                inputLogicPolarity="Normal",
                arrayCounter=completed_steps,
                arrayCallbacks=True))]
        self.o.post_configure.assert_called_once_with(
            self.context.block_view(), params)
