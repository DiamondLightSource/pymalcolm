import unittest

from mock import patch

from malcolm.core import Process
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.pmac.parts import CSSourcePortsPart


class castr(str):
    ok = True
    severity = 0


class TestCSOutlinksPart(unittest.TestCase):
    @patch("malcolm.modules.ca.util.catools")
    def setUp(self, catools):
        self.catools = catools
        catools.caget.side_effect = [[castr("BRICK1CS1")]]
        self.process = Process("proc")
        self.o = CSSourcePortsPart("cs", "PV:PRE:Port")
        c = StatefulController("mri")
        c.add_part(self.o)
        self.process.add_controller(c)
        self.b = self.process.block_view("mri")
        self.process.start()
        self.addCleanup(self.process.stop)

    def test_init(self):
        self.catools.caget.assert_called_once_with(
            ["PV:PRE:Port"],
            datatype=self.catools.DBR_STRING,
            format=self.catools.FORMAT_CTRL,
            throw=True,
        )
        assert list(self.b) == [
            "meta",
            "health",
            "state",
            "disable",
            "reset",
            "cs",
            "a",
            "b",
            "c",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
            "i",
        ]
        assert self.b.cs.value == "BRICK1CS1"
        assert self.b.a.value == ""
        assert self.b.a.meta.tags == ["sourcePort:motor:BRICK1CS1,A"]
        assert self.b.v.value == ""
        assert self.b.v.meta.tags == ["sourcePort:motor:BRICK1CS1,V"]
        assert self.b.i.value == ""
        assert self.b.i.meta.tags == ["sourcePort:motor:BRICK1CS1,I"]
