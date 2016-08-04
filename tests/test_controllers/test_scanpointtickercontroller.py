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

    @patch("malcolm.core.vmetas.StringMeta.to_dict")
    @patch("malcolm.core.vmetas.NumberMeta.to_dict")
    @patch("malcolm.core.vmetas.PointGeneratorMeta.to_dict")
    def test_init(self, pgmd_mock, nmd_mock, smd_mock):
        del pgmd_mock.return_value.to_dict
        del nmd_mock.return_value.to_dict
        del smd_mock.return_value.to_dict
        attr_id = "epics:nt/NTAttribute:1.0"
        sptc = ScanPointTickerController('block', MagicMock())
        self.assertEqual(RunnableDeviceStateMachine, type(sptc.stateMachine))
        self.assertEqual("RunnableDeviceStateMachine", sptc.stateMachine.name)
        self.assertEquals(
            {"value": None, "meta": nmd_mock.return_value, "typeid": attr_id},
            sptc.value.to_dict())
        self.assertEquals(
            {"value": None, "meta": pgmd_mock.return_value, "typeid": attr_id},
            sptc.generator.to_dict())
        self.assertEquals(
            {"value": None, "meta": smd_mock.return_value, "typeid": attr_id},
            sptc.axis_name.to_dict())
        self.assertEquals(
            {"value": None, "meta": nmd_mock.return_value, "typeid": attr_id},
            sptc.exposure.to_dict())

    def test_configure(self):
        params = MagicMock()
        with patch("malcolm.core.vmetas.CompoundGenerator",
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
        with patch("malcolm.core.vmetas.CompoundGenerator",
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
