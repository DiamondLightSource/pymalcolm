import os
import sys
import socket

from pkg_resources import require

require("numpy", "tornado", "cothread")

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
        pass

    def test_double(self):
        pvname = "%s:CAM:AcquireTime" % self.prefix
        d = {"name": "pv",
             "description": "a test pv",
             "pv": pvname,
             "rbv_suff": "_RBV"}
        p = CADoublePart("p", self.process, self.block, d)
        p.connect_pvs()

        for i in range(1, 6):
            f = i / 2.0
            p.caput(f)
            self.assertEqual(p.attr.value, f)

        p.close_monitor()

    def test_choice(self):
        pvname = "%s:CAM:DataType" % self.prefix
        d = {"name": "pv",
             "description": "a test pv",
             "pv": pvname,
             "rbv_suff": "_RBV"}
        p = CAChoicePart("p", self.process, self.block, d)
        p.connect_pvs()

        for i in [1, 5]:
            p.caput(i)
            self.assertEqual(p.attr.value, i)

        self.assertItemsEqual(p.attr.meta.choices,
                              ['Int8', 'UInt8', 'Int16', 'UInt16', 'Int32',
                               'UInt32', 'Float32', 'Float64'])
        p.close_monitor()

    def test_long(self):
        pvname = "%s:CAM:BinX" % self.prefix
        d = {"name": "pv",
             "description": "a test pv",
             "pv": pvname,
             "rbv_suff": "_RBV"}
        p = CALongPart("p", self.process, self.block, d)
        p.connect_pvs()

        for i in range(1, 6):
            f = i / 2.0
            p.caput(f)
            self.assertEqual(p.attr.value, int(f))

        p.close_monitor()

    def test_string(self):
        pvname = "%s:ROI:Name" % self.prefix
        d = {"name": "pv",
             "description": "a test pv",
             "pv": pvname,
             "rbv_suff": "_RBV"}
        p = CAStringPart("p", self.process, self.block, d)
        p.connect_pvs()

        for s in ["Hello", "World", "Again"]:
            p.caput(s)
            self.assertEqual(p.attr.value, s)

        p.close_monitor()

    def test_doublearray(self):
        pvname = "%s:STAT:Histogram_RBV" % self.prefix
        d = {"name": "pv",
             "description": "a test pv",
             "rbv": pvname}
        p = CADoubleArrayPart("p", self.process, self.block, d)

        # this is a read only PV - just check we read it
        p.connect_pvs()
        da = [0] * len(p.attr.value)
        self.assertItemsEqual(p.attr.value, da)
        p.close_monitor()

    def test_chararray(self):
        pvname = "%s:CAM:NDAttributesFile" % self.prefix
        d = {"name": "pv",
             "description": "a test pv",
             "pv": pvname,
             "rbv_suff": ""}
        p = CACharArrayPart("p", self.process, self.block, d)

        # this is a read only PV
        p.connect_pvs()

        for s in ['Testing', '1111', '2222']:
            p.caput(s)
            self.assertEqual(p.attr.value, s)

        p.close_monitor()
