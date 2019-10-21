import unittest
from mock import Mock, call

from malcolm.modules.scanning.parts import ShutterPart
from malcolm.modules.scanning.hooks import RunHook, ConfigureHook, ResumeHook, \
    PauseHook, AbortHook, PostRunReadyHook


class TestShutterPartConstructor(unittest.TestCase):

    def setUp(self):
        self.name = "ShutterPart"
        self.description = "This is a ShutterPart"
        self.pv = "TEST:PV"
        self.open_value = "Open"
        self.close_value = "Close"

    def test_attributes_are_initialised_with_defaults(self):
        part = ShutterPart(self.name, self.description, self.open_value, self.close_value, pv=self.pv)

        self.assertEqual(self.name, part.name)
        self.assertEqual(self.open_value, part.open_value)
        self.assertEqual(self.close_value, part.close_value)
        self.assertEqual(False, part.open_during_run)

    def test_open_during_run_is_set_when_provided(self):
        part = ShutterPart(
            self.name, self.description, self.open_value, self.close_value, pv=self.pv, open_during_run=True)

        self.assertEqual(self.name, part.name)
        self.assertEqual(self.open_value, part.open_value)
        self.assertEqual(self.close_value, part.close_value)
        self.assertEqual(True, part.open_during_run)


class TestShutterPartShutterControl(unittest.TestCase):

    def setUp(self):
        name = "ShutterPart"
        description = "This is a ShutterPart"
        pv = "TEST:PV"
        self.open_value = "Open"
        self.close_value = "Close"
        self.part = ShutterPart(name, description, self.open_value, self.close_value, pv=pv)
        self.part.setup(Mock())

    def test_open_shutter_calls_caput(self):
        self.part.caput = Mock()
        self.part.open_shutter()
        self.part.caput.assert_called_once_with(self.open_value)

    def test_close_shutter_calls_caput(self):
        self.part.caput = Mock()
        self.part.close_shutter()
        self.part.caput.assert_called_once_with(self.close_value)


class TestShutterPartSetupHooks(unittest.TestCase):

    def setUp(self):
        self.name = "ShutterPart"
        self.description = "This is a ShutterPart"
        self.pv = "TEST:PV"
        self.open_value = "Open"
        self.close_value = "Close"

    def test_setup_open_shutter_during_RunHook_if_open_during_run_True(self):
        self.part = ShutterPart(self.name, self.description, self.open_value, self.close_value, pv=self.pv,
                                open_during_run=True)
        registrar_mock = Mock()
        self.part.setup(registrar_mock)

        # Check calls
        calls = [
            call(RunHook, self.part.open_shutter),
            call(ResumeHook, self.part.open_shutter),
            call(PauseHook, self.part.close_shutter),
            call(AbortHook, self.part.close_shutter),
            call(PostRunReadyHook, self.part.close_shutter)
            ]
        registrar_mock.hook.assert_has_calls(calls)

    def test_setup_open_shutter_during_ConfigureHook_if_open_during_run_False(self):
        self.part = ShutterPart(self.name, self.description, self.open_value, self.close_value, pv=self.pv,
                                open_during_run=False)
        registrar_mock = Mock()
        self.part.setup(registrar_mock)

        # Check calls
        calls = [
            call(ConfigureHook, self.part.open_shutter),
            call(ResumeHook, self.part.open_shutter),
            call(PauseHook, self.part.close_shutter),
            call(AbortHook, self.part.close_shutter),
            call(PostRunReadyHook, self.part.close_shutter)
            ]
        registrar_mock.hook.assert_has_calls(calls)
