import unittest

from mock import Mock, patch

from malcolm.core import Process
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.ca.parts import CAActionPart


class caint(int):
    ok = True


class ca_nothing(object):
    ok = False


@patch("malcolm.modules.ca.util.catools")
class TestCAActionPart(unittest.TestCase):
    def create_part(self, params=None):
        if params is None:
            params = dict(
                name="mname",
                description="desc",
                pv="pv",
            )

        p = CAActionPart(**params)
        p.setup(Mock())
        return p

    def test_init(self, catools):
        p = self.create_part()
        assert p.pv == "pv"
        assert p.value == 1
        assert p.wait is True
        assert p.description == "desc"
        p.registrar.add_method_model.assert_called_once_with(p.caput, "mname", "desc")

    def test_reset(self, catools):
        catools.ca_nothing = ca_nothing
        p = self.create_part()
        catools.caget.reset_mock()
        catools.caget.return_value = [caint(4)]
        p.reconnect()
        catools.caget.assert_called_with(["pv"], throw=True)

    def test_caput(self, catools):
        p = self.create_part()
        catools.caput.reset_mock()
        p.caput()
        catools.caput.assert_called_once_with("pv", 1, wait=True, timeout=None)

    def make_camonitor_return(self, catools, values):
        if not isinstance(values, (list, tuple)):
            values = [values]

        def side_effect(pv, cb, **kwargs):
            for v in values:
                cb(v)
            return Mock()

        catools.camonitor.side_effect = side_effect

    def test_caput_status_pv_ok(self, catools):
        p = self.create_part(
            dict(
                name="mname",
                description="desc",
                pv="pv",
                status_pv="spv",
                good_status="All Good",
            )
        )

        self.make_camonitor_return(catools, ["Still going", "All Good"])
        p.caput()

    def test_caput_status_pv_no_good(self, catools):
        p = self.create_part(
            dict(
                name="mname",
                description="desc",
                pv="pv",
                status_pv="spv",
                good_status="All Good",
            )
        )
        self.make_camonitor_return(catools, "No Good")
        with self.assertRaises(AssertionError) as cm:
            p.caput()
        assert str(cm.exception) == "Status No Good: while performing 'caput pv 1'"

    def test_caput_status_pv_message(self, catools):
        p = self.create_part(
            dict(
                name="mname",
                description="desc",
                pv="pv",
                status_pv="spv",
                good_status="All Good",
                message_pv="mpv",
            )
        )
        catools.caget.return_value = [caint(4)]
        c = StatefulController("mri")
        c.add_part(p)
        proc = Process("proc")
        proc.add_controller(c)
        proc.start()
        self.addCleanup(proc.stop)
        b = proc.block_view("mri")
        self.make_camonitor_return(catools, "No Good")
        catools.caget.return_value = "Bad things happened"
        with self.assertRaises(AssertionError) as cm:
            b.mname()
        assert (
            str(cm.exception) == "Status No Good: Bad things happened: "
            "while performing 'caput pv 1'"
        )
