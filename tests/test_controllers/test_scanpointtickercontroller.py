import os
import sys
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
from mock import MagicMock, patch, call

from malcolm.core.statemachine import RunnableDeviceStateMachine
from malcolm.controllers import ScanPointTickerController
from malcolm.core.block import Block


class TestScanPointTickerController(unittest.TestCase):

    def test_configure(self):
        params = MagicMock()
        with patch("malcolm.core.vmetas.pointgeneratormeta.CompoundGenerator",
                   spec=True) as cg_mock:
            params.generator = cg_mock()
        params.exposure = 1
        params.axis_name = "x"
        sptc = ScanPointTickerController('block', MagicMock())

        sptc.configure(params)

        self.assertEqual(params.generator, sptc.generator.value)
        self.assertEqual(params.axis_name, sptc.axis_name.value)
        self.assertEqual(params.exposure, sptc.exposure.value)

    @patch("malcolm.controllers.scanpointtickercontroller.time")
    def test_run(self, time_mock):
        points = [MagicMock(positions=dict(x=i)) for i in range(5)]
        params = MagicMock()
        with patch("malcolm.core.vmetas.pointgeneratormeta.CompoundGenerator",
                   spec=True) as cg_mock:
            params.generator = cg_mock()
        params.exposure = 2.0
        params.axis_name = "x"
        params.generator.iterator = MagicMock(return_value=points)
        sptc = ScanPointTickerController('block', MagicMock())
        sptc.value.set_value = MagicMock(side_effect=sptc.value.set_value)

        sptc.configure(params)
        sptc.run()

        self.assertEquals([call(i) for i in range(5)],
                          sptc.value.set_value.call_args_list)
        self.assertEquals([call(params.exposure)] * 5,
                          time_mock.sleep.call_args_list)

if __name__ == "__main__":
    unittest.main(verbosity=2)
