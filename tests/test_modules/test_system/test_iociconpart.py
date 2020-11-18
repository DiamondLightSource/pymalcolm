import os
import unittest

from mock import ANY, patch

from malcolm.core import Context, Process, StringMeta
from malcolm.modules.ca.util import catools
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.system.parts import IocIconPart

defaultIcon = ""
with open(
    os.path.split(__file__)[0] + "/../../../malcolm/modules/system/icons/epics-logo.svg"
) as f:
    defaultIcon = f.read()

vxIcon = ""
with open(
    os.path.split(__file__)[0] + "/../../../malcolm/modules/system/icons/vx_epics.svg"
) as f:
    vxIcon = f.read()

linuxIcon = ""
with open(
    os.path.split(__file__)[0]
    + "/../../../malcolm/modules/system/icons/linux_epics.svg"
) as f:
    linuxIcon = f.read()

winIcon = ""
with open(
    os.path.split(__file__)[0] + "/../../../malcolm/modules/system/icons/win_epics.svg"
) as f:
    winIcon = f.read()


class MockPv(str):
    ok = True


class TestIocIconPart(unittest.TestCase):
    def add_part_and_start(self):
        self.icon = IocIconPart(
            "ICON",
            os.path.split(__file__)[0]
            + "/../../../malcolm/modules/system/icons/epics-logo.svg",
        )
        self.c1.add_part(self.icon)
        self.p.add_controller(self.c1)
        self.p.start()

    def setUp(self):
        self.p = Process("process1")
        self.context = Context(self.p)
        self.c1 = RunnableController(mri="SYS", config_dir="/tmp", use_git=False)

    def tearDown(self):
        self.p.stop(timeout=1)

    @patch("malcolm.modules.ca.util.CAAttribute")
    def test_has_pv(self, CAAttribute):
        self.add_part_and_start()
        CAAttribute.assert_called_once_with(
            ANY,
            catools.DBR_STRING,
            "",
            "ICON:KERNEL_VERS",
            throw=False,
            callback=self.icon.update_icon,
        )
        assert isinstance(CAAttribute.call_args[0][0], StringMeta)
        meta = CAAttribute.call_args[0][0]
        assert meta.description == "Host Architecture"
        assert not meta.writeable
        assert len(meta.tags) == 0

    def test_adds_correct_icons(self):
        self.add_part_and_start()
        assert self.context.block_view("SYS").icon.value == defaultIcon

        arch = MockPv("windows")
        self.icon.update_icon(arch)
        assert self.context.block_view("SYS").icon.value == winIcon

        arch = MockPv("WIND")
        self.icon.update_icon(arch)
        assert self.context.block_view("SYS").icon.value == vxIcon

        arch = MockPv("linux")
        self.icon.update_icon(arch)
        assert self.context.block_view("SYS").icon.value == linuxIcon
