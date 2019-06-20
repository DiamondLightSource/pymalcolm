import unittest

from malcolm.core import Process
from malcolm.modules.stats.controllers import StatsController

from malcolm.version import __version__
from cothread import catools
import time
import os
from math import floor


class TestBasicController(unittest.TestCase):
    prefix = "unitTest:%s" % floor(time.time()).__repr__()[:-2]

    def setUp(self):
        self.process = Process("proc")
        self.o = StatsController("MyMRI", prefix=self.prefix)
        self.process.add_controller(self.o)
        self.process.start()
        self.b = self.process.block_view("MyMRI")

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_sets_stats(self):
        assert self.b.pymalcolmVer.value == __version__
        assert self.b.hostname.value == os.uname()[1]

    def test_starts_ioc(self):
        assert catools.caget(self.prefix + ":PYMALCOLM:VER") == __version__

    def test_ioc_ticks(self):
        uptime = catools.caget(self.prefix + ":UPTIME:RAW")
        assert uptime >= 0
        time.sleep(5)
        assert catools.caget(self.prefix + ":UPTIME:RAW") >= uptime + 5
