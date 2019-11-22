import unittest
from mock import Mock, call

from malcolm.modules.scanning.parts import AttributePreRunPart
from malcolm.modules.scanning.hooks import PreRunHook, \
    PauseHook, AbortHook, PostRunReadyHook


class TestAttributePreRunPartConstructor(unittest.TestCase):

    def setUp(self):
        self.name = "ShutterPart"
        self.mri = "ML-SHUTTER-01"
        self.pre_run_value = "Open"
        self.reset_value = "Closed"

    def test_attributes_are_initialised_with_defaults(self):
        part = AttributePreRunPart(self.name, self.mri, self.pre_run_value, self.reset_value)

        self.assertEqual(self.name, part.name)
        self.assertEqual(self.mri, part.mri)
        self.assertEqual(self.pre_run_value, part.pre_run_value)
        self.assertEqual(self.reset_value, part.reset_value)


class TestAttributePreRunPartSetupHooks(unittest.TestCase):

    def setUp(self):
        self.name = "ShutterPart"
        self.description = "This is a ShutterPart"
        self.pre_run_value = "Open"
        self.reset_value = "Closed"

    def test_setup_sets_correct_hooks(self):
        self.part = AttributePreRunPart(self.name, self.description, self.pre_run_value, self.reset_value)
        registrar_mock = Mock()
        self.part.setup(registrar_mock)

        # Check calls
        calls = [
            call(PreRunHook, self.part.on_pre_run),
            call((PauseHook, AbortHook, PostRunReadyHook), self.part.reset),
            ]
        registrar_mock.hook.assert_has_calls(calls)


class TestAttributePreRunPartPutMethods(unittest.TestCase):

    def setUp(self):
        # Create our part
        name = "ShutterPart"
        mri = "ML-SHUTTER-01"
        self.pre_run_value = "Open"
        self.reset_value = "Closed"
        self.part = AttributePreRunPart(name, mri, self.pre_run_value, self.reset_value)
        # Generate our mocks
        self.part.setup(Mock())
        self.context = Mock(name='context')
        self.child = Mock(name='child')
        self.context.block_view.return_value = self.child

    def test_open_shutter_puts_open_value_to_child(self):
        self.part.on_pre_run(self.context)
        self.child.shutter.put_value.assert_called_once_with(self.pre_run_value)

    def test_close_shutter_puts_closed_value_to_child(self):
        self.part.reset(self.context)
        self.child.shutter.put_value.assert_called_once_with(self.reset_value)
