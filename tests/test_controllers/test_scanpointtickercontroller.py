import os
import sys
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
from mock import MagicMock, patch, call

from malcolm.core.attribute import Attribute
from malcolm.core.runnabledevicestatemachine import RunnableDeviceStateMachine
from malcolm.controllers.scanpointtickercontroller import \
    ScanPointTickerController


class TestScanPointTickerController(unittest.TestCase):

    @patch("malcolm.core.stringmeta.StringMeta.to_dict")
    @patch("malcolm.core.numbermeta.NumberMeta.to_dict")
    @patch("malcolm.core.pointgeneratormeta.PointGeneratorMeta.to_dict")
    def test_init(self, pgmd_mock, nmd_mock, smd_mock):
        attr_id = "malcolm:core/Attribute:1.0"
        block = MagicMock()
        sptc = ScanPointTickerController(block)
        self.assertEqual(block, sptc.block)
        self.assertEqual(RunnableDeviceStateMachine, type(sptc.stateMachine))
        self.assertEqual("RunnableDeviceStateMachine", sptc.stateMachine.name)
        self.assertEquals(
            {"value":None, "meta":nmd_mock.return_value, "typeid":attr_id},
            sptc.value.to_dict())
        self.assertEquals(
            {"value":None, "meta":pgmd_mock.return_value, "typeid":attr_id},
            sptc.generator.to_dict())
        self.assertEquals(
            {"value":None, "meta":smd_mock.return_value, "typeid":attr_id},
            sptc.axis_name.to_dict())
        self.assertEquals(
            {"value":None, "meta":nmd_mock.return_value, "typeid":attr_id},
            sptc.exposure.to_dict())

    def test_configure(self):
        g = MagicMock()
        an = MagicMock()
        e = MagicMock()
        block = MagicMock()
        sptc = ScanPointTickerController(block)

        sptc.configure(g, an, e)

        self.assertEqual(g, sptc.generator.value)
        self.assertEqual(an, sptc.axis_name.value)
        self.assertEqual(e, sptc.exposure.value)
        block.notify_subscribers.assert_called_once_with()

    @patch("time.sleep")
    def test_run(self, sleep_mock):
        points = [MagicMock(), MagicMock(), MagicMock()]
        g = MagicMock()
        g.iterator = MagicMock(return_value=points)
        an = MagicMock()
        e = MagicMock()
        e.__float__ = MagicMock(return_value=0.1)
        block = MagicMock()
        sptc = ScanPointTickerController(block)
        sptc.value.set_value = MagicMock(side_effect=sptc.value.set_value)

        sptc.configure(g, an, e)
        block.reset_mock()
        sptc.run()

        self.assertEquals([call(p) for p in points],
                          sptc.value.set_value.call_args_list)
        self.assertEquals([call(e)] * len(points), sleep_mock.call_args_list)
        self.assertEqual([call()] * 3, block.notify_subscribers.call_args_list)

if __name__ == "__main__":
    unittest.main(verbosity=2)
