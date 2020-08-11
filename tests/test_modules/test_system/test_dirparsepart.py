import os
import time
import unittest

from mock import patch

from malcolm.core import Context, Process
from malcolm.core.alarm import Alarm, AlarmSeverity
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.system.parts import DirParsePart

deps = ["TEST=/a/test\n", "DEP1=$(TEST)/some/dependency\n"]

now = "%s" % time.time()


class MockPv(str):
    ok = True


class ManyAlarms:
    def __iter__(self):
        self.i = 1
        return self

    def __next__(self):
        self.i += 1
        return Alarm(message="Alarm #%s" % self.i)


def reset_alarms(mock):
    mock.reset_mock()
    mock.side_effect = iter(ManyAlarms())


class TestDirParsePart(unittest.TestCase):
    @patch("malcolm.modules.ca.util.catools")
    def add_part_and_start(self, catools):
        self.part = DirParsePart("dir", "TS-DI-IOC-01")

        self.c1.add_part(self.part)
        self.p.add_controller(self.c1)
        self.p.start()

    def setUp(self):
        self.p = Process("process1")
        self.context = Context(self.p)
        self.c1 = RunnableController(mri="SYS", config_dir="/tmp", use_git=False)
        self.tmp_dir = "/tmp/%s-%s" % (now, os.getpid())
        os.mkdir(self.tmp_dir)
        os.mkdir(self.tmp_dir + "/configure")

    def tearDown(self):
        try:
            self.p.stop(timeout=1)
        except AssertionError:
            pass
        try:
            os.rmdir(self.tmp_dir + "/configure")
            os.rmdir(self.tmp_dir)
        except OSError:
            # directory doesn't exist
            pass

    # @patch("malcolm.modules.ca.util.CAAttribute")
    # def test_has_pvs(self, CAAttribute):
    #     self.add_part_and_start()
    #     CAAttribute.assert_called_once_with(
    #         ANY, catools.DBR_STRING, "", "ICON:KERNEL_VERS", throw=False)
    #     assert isinstance(CAAttribute.call_args[0][0], StringMeta)
    #     meta = CAAttribute.call_args[0][0]
    #     assert meta.description == "Host Architecture"
    #     assert not meta.writeable
    #     assert len(meta.tags) == 0

    def test_set_dir_concats_strings(self):
        self.add_part_and_start()
        self.part.dir1 = "hello "
        self.part.set_dir2(MockPv("world!"))
        assert self.part.dir == "hello world!"

        self.part.dir2 = "bar"
        self.part.set_dir1(MockPv("foo"))
        assert self.part.dir == "foobar"

    def test_parses_dir(self):
        self.add_part_and_start()
        self.part.dir = self.tmp_dir
        with open(self.tmp_dir + "/configure/RELEASE", "w") as f:
            f.writelines(deps)
        self.part.parse_release()
        assert len(self.part.dependencies.value.module) == 2
        assert len(self.part.dependencies.value.path) == 2
        assert self.part.dependencies.value.module[0] == "TEST"
        assert self.part.dependencies.value.module[1] == "DEP1"
        assert self.part.dependencies.value.path[0] == "/a/test"
        assert self.part.dependencies.value.path[1] == "/a/test/some/dependency"

        os.remove(self.tmp_dir + "/configure/RELEASE")

    @patch("malcolm.core.alarm.Alarm")
    def test_sets_alarm_if_dir_doesnt_exist(self, alarm):
        reset_alarms(alarm)
        self.add_part_and_start()
        self.part.dir = "/i/am/not/a/dir"
        reset_alarms(alarm)
        self.part.parse_release()
        alarm.assert_called_with(
            message="reported IOC directory not found",
            severity=AlarmSeverity.MINOR_ALARM,
        )

    @patch("malcolm.core.alarm.Alarm")
    def test_version_updated_sets_status_for_version(self, alarm):
        reset_alarms(alarm)
        self.add_part_and_start()
        reset_alarms(alarm)
        self.part.version_updated(MockPv("work"))
        alarm.assert_called_once_with(
            message="IOC running from non-prod area", severity=AlarmSeverity.MINOR_ALARM
        )
        reset_alarms(alarm)
        self.part.version_updated(MockPv("other"))
        alarm.assert_called_once_with(
            message="IOC running from non-prod area", severity=AlarmSeverity.MINOR_ALARM
        )
        reset_alarms(alarm)
        self.part.version_updated(MockPv("somethingelse"))
        alarm.assert_called_once_with(message="OK", severity=AlarmSeverity.NO_ALARM)

    @patch("malcolm.core.alarm.Alarm")
    def test_version_updated_sets_alarm_if_no_version(self, alarm):
        reset_alarms(alarm)
        self.add_part_and_start()
        reset_alarms(alarm)
        self.part.has_procserv = True
        self.part.version_updated(None)
        alarm.assert_called_once_with(
            message="IOC not running (procServ enabled)",
            severity=AlarmSeverity.UNDEFINED_ALARM,
        )
        reset_alarms(alarm)
        self.part.has_procserv = False
        self.part.version_updated(None)
        alarm.assert_called_once_with(
            message="neither IOC nor procServ are running",
            severity=AlarmSeverity.INVALID_ALARM,
        )
