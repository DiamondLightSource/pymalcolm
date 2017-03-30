import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import socket

from pkg_resources import require

require("numpy", "tornado", "cothread", "scanpointgenerator")

from malcolm.parts.ca import CADoublePart, CAChoicePart, CALongPart, \
    CAStringPart, CADoubleArrayPart, CACharArrayPart
from malcolm.core import Block, Process, SyncFactory

import unittest


# System tests for the CAParts subclasses

# NOTE: these tests require an instance of the GDA AreaDetector Simulation
# running and that the test process is launched with
# export EPICS_CA_SERVER_PORT = 6064;
# export EPICS_CA_REPEATER_PORT = 6065


class CAPartsTest(unittest.TestCase):
    def setUp(self):
        self.sync = SyncFactory("threads")
        self.process = Process("proc", self.sync)
        self.host = socket.gethostname().split('.')[0]
        self.prefix = "%s-AD-SIM-01" % self.host

    def create_part(self, cls, **args):
        params = cls.MethodMeta.prepare_input_map(args)
        p = cls(self.process, params)
        p.set_logger_name(cls.__name__)
        list(p.create_attributes())
        p.reset()
        return p

    def test_double(self):
        p = self.create_part(
            CADoublePart,
            name="pv",
            description="a test pv",
            pv="%s:CAM:AcquireTime" % self.prefix,
            rbv_suff="_RBV")

        for i in range(1, 6):
            f = i / 2.0
            p.caput(f)
            self.assertEqual(p.attr.value, f)

        p.close_monitor()

    def test_choice(self):
        p = self.create_part(
            CAChoicePart,
            name="pv",
            description="a test pv",
            pv="%s:CAM:DataType" % self.prefix,
            rbv_suff="_RBV")

        for i in [1, 5]:
            p.caput(i)
            self.assertEqual(p.attr.value, i)

        self.assertItemsEqual(p.attr.meta.choices,
                              ['Int8', 'UInt8', 'Int16', 'UInt16', 'Int32',
                               'UInt32', 'Float32', 'Float64'])
        p.close_monitor()

    def test_long(self):
        p = self.create_part(
            CALongPart,
            name="pv",
            description="a test pv",
            pv="%s:CAM:BinX" % self.prefix,
            rbv_suff="_RBV")

        for i in range(1, 6):
            f = i / 2.0
            p.caput(f)
            self.assertEqual(p.attr.value, int(f))

        p.close_monitor()

    def test_string(self):
        p = self.create_part(
            CAStringPart,
            name="pv",
            description="a test pv",
            pv="%s:ROI:Name" % self.prefix,
            rbv_suff="_RBV")

        for s in ["Hello", "World", "Again"]:
            p.caput(s)
            self.assertEqual(p.attr.value, s)

        p.close_monitor()

    def test_doublearray(self):
        p = self.create_part(
            CAStringPart,
            name="pv",
            description="a test pv",
            rbv="%s:STAT:Histogram_RBV" % self.prefix)

        # this is a read only PV - just check we read it
        da = [0] * len(p.attr.value)
        self.assertItemsEqual(p.attr.value, da)
        p.close_monitor()

    def test_chararray(self):
        p = self.create_part(
            CACharArrayPart,
            name="pv",
            description="a test pv",
            pv="%s:CAM:NDAttributesFile" % self.prefix,
            rbv_suff="")

        for s in ['Testing', '1111', '2222']:
            p.caput(s)
            self.assertEqual(p.attr.value, s)

        p.close_monitor()

if __name__ == "__main__":
    unittest.main(verbosity=2)