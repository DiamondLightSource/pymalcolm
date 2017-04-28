import unittest
import functools
from mock import Mock, patch

from malcolm.core import call_with_params, Context, Process
from malcolm.modules.pmac.parts import CompoundMotorPart
from malcolm.modules.pmac.blocks import compound_motor_block


class TestRawMotorPart(unittest.TestCase):

    @patch("malcolm.modules.ca.parts.capart.CAPart.reset")
    @patch("malcolm.modules.ca.parts.catoolshelper.CaToolsHelper._instance")
    def setUp(self, catools, reset):
        self.put = Mock(return_value=None)
        self.process = Process("Process")
        self.context = Context(self.process)
        child = call_with_params(
            compound_motor_block, self.process, mri="my_mri", prefix="PV:PRE",
            scannable="scan")
        for k in child._write_functions:
            child._write_functions[k] = functools.partial(self.put, k)
        child.parts["maxVelocity"].attr.set_value(5.0)
        child.parts["accelerationTime"].attr.set_value(0.5)
        child.parts["position"].attr.set_value(12.3)
        child.parts["offset"].attr.set_value(4.5)
        child.parts["resolution"].attr.set_value(0.001)
        child.parts["outLink"].attr.set_value("@asyn(CS_PORT,2)")
        self.o = call_with_params(CompoundMotorPart, name="part", mri="my_mri")
        list(self.o.create_attributes())
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop()

    def test_report(self):
        returns = self.o.report_cs_info(self.context)[0]
        self.assertEqual(returns.cs_axis, "B")
        self.assertEqual(returns.cs_port, "CS_PORT")
        self.assertEqual(returns.acceleration, 10.0)
        self.assertEqual(returns.resolution, 1.0)
        self.assertEqual(returns.offset, 4.5)
        self.assertEqual(returns.max_velocity, 5.0)
        self.assertEqual(returns.current_position, 12.3)
        self.assertEqual(returns.scannable, "scan")


if __name__ == "__main__":
    unittest.main(verbosity=2)
