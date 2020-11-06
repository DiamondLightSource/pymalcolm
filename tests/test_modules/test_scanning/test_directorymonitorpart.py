import unittest

from mock import Mock

from malcolm.modules.scanning.hooks import ConfigureHook
from malcolm.modules.scanning.parts import DirectoryMonitorPart


class TestDirectoryMonitorPartConstructor(unittest.TestCase):
    def setUp(self):
        self.name = "DirectoryMonitorPart"
        self.mri = "ML-DIRMON-01"

    def test_attributes_are_initialised(self):
        part = DirectoryMonitorPart(self.name, self.mri)

        self.assertEqual(self.name, part.name)
        self.assertEqual(self.mri, part.mri)


class TestDirectoryMonitorPartSetupHooks(unittest.TestCase):
    def setUp(self):
        self.name = "DirectoryMonitorPart"
        self.mri = "ML-DIRMON-01"

    def test_hooks_are_set(self):
        part = DirectoryMonitorPart(self.name, self.mri)

        registrar_mock = Mock()
        part.setup(registrar_mock)

        registrar_mock.hook.assert_called_with(ConfigureHook, part.check_directories)


class TestDirectoryMonitorPartCheckManagerMethod(unittest.TestCase):
    def setUp(self):
        self.name = "DirectoryMonitorPart"
        self.mri = "ML-DIRMON-01"
        self.hostname = "TEST-SERVER"
        self.part = DirectoryMonitorPart(self.name, self.mri)
        self.expected_bad_status_string = (
            f"{self.mri}: bad directory monitor status for server {self.hostname}"
        )

        # Mocks
        self.context = Mock(name="context")
        self.child = Mock(name="child")
        self.context.block_view.return_value = self.child
        self.child.managerHostname.value = self.hostname

    def test_method_checks_and_get_status(self):
        self.part.setup(Mock())
        self.part.check_directories(self.context)

        self.child.managerCheck.assert_called_once
        self.child.managerStatus.value.assert_called_once

    def test_method_raises_ValueErorr_for_bad_managerCheck_status(self):
        self.child.managerCheck = Mock(
            name="managerCheck", side_effect=AssertionError()
        )
        self.part.log = Mock(name="logger")

        self.assertRaises(ValueError, self.part.check_directories, self.context)
        self.part.log.error.assert_called_once_with(self.expected_bad_status_string)

    def test_method_logs_error_for_bad_managerCheck_status(self):
        self.child.managerCheck = Mock(
            name="managerCheck", side_effect=AssertionError()
        )
        self.part.error_on_fail = False
        self.part.log = Mock(name="logger")

        self.part.check_directories(self.context)

        self.part.log.error.assert_called_once_with(self.expected_bad_status_string)
