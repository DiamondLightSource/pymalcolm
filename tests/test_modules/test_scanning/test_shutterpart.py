import unittest
from mock import Mock, call

from malcolm.modules.scanning.parts import ShutterPart
from malcolm.modules.scanning.hooks import PreRunHook, \
    PauseHook, AbortHook, PostRunReadyHook


class TestShutterPartConstructor(unittest.TestCase):

    def setUp(self):
        self.name = "ShutterPart"
        self.mri = "ML-SHUTTER-01"
        self.open_value = "Open"
        self.closed_value = "Closed"

    def test_attributes_are_initialised_with_defaults(self):
        part = ShutterPart(self.name, self.mri, self.open_value, self.closed_value)

        self.assertEqual(self.name, part.name)
        self.assertEqual(self.mri, part.mri)
        self.assertEqual(self.open_value, part.open_value)
        self.assertEqual(self.closed_value, part.closed_value)


class TestShutterPartSetupHooks(unittest.TestCase):

    def setUp(self):
        self.name = "ShutterPart"
        self.description = "This is a ShutterPart"
        self.open_value = "Open"
        self.closed_value = "Closed"

    def test_setup_sets_correct_hooks(self):
        self.part = ShutterPart(self.name, self.description, self.open_value, self.closed_value)
        registrar_mock = Mock()
        self.part.setup(registrar_mock)

        # Check calls
        calls = [
            call(PreRunHook, self.part.open_shutter),
            call((PauseHook, AbortHook, PostRunReadyHook), self.part.close_shutter),
            ]
        registrar_mock.hook.assert_has_calls(calls)


class TestShutterPartShutterControl(unittest.TestCase):

    def setUp(self):
        # Create our part
        name = "ShutterPart"
        mri = "ML-SHUTTER-01"
        self.open_value = "Open"
        self.closed_value = "Closed"
        self.part = ShutterPart(name, mri, self.open_value, self.closed_value)
        # Generate our mocks
        self.part.setup(Mock())
        self.context = Mock(name='context')
        self.child = Mock(name='child')
        self.context.block_view.return_value = self.child

    def test_open_shutter_puts_open_value_to_child(self):
        self.part.open_shutter(self.context)
        self.child.shutter.put_value.assert_called_once_with(self.open_value)

    def test_close_shutter_puts_closed_value_to_child(self):
        self.part.close_shutter(self.context)
        self.child.shutter.put_value.assert_called_once_with(self.closed_value)
