import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, ANY, call

from malcolm.parts.xmap.xmapdriverpart import XmapDriverPart


class TestXmap3DetectorDriverPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.params.readoutTime = 0.002
        self.process.get_block.return_value = self.child
        self.o = XmapDriverPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        completed_steps = MagicMock()
        steps_to_do = MagicMock()
        part_info = ANY
        self.o.post_configure = MagicMock()
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        task.put_many.assert_called_once_with(self.child, dict(
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
            arrayCallbacks=True))
        self.o.post_configure.assert_called_once_with(task, params)


if __name__ == "__main__":
    unittest.main(verbosity=2)
