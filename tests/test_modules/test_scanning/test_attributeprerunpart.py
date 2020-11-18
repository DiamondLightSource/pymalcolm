import unittest

from mock import Mock, call

from malcolm.modules.scanning.hooks import (
    AbortHook,
    PauseHook,
    PostRunReadyHook,
    PreRunHook,
)
from malcolm.modules.scanning.parts import AttributePreRunPart


class TestAttributePreRunPartConstructor(unittest.TestCase):
    def setUp(self):
        self.name = "ShutterPart"
        self.mri = "ML-SHUTTER-01"
        self.pre_run_value = "Open"
        self.reset_value = "Closed"

    def test_attributes_are_initialised_with_defaults(self):
        part = AttributePreRunPart(
            self.name, self.mri, self.pre_run_value, self.reset_value
        )

        self.assertEqual(self.name, part.name)
        self.assertEqual(self.mri, part.mri)
        self.assertEqual(self.pre_run_value, part.pre_run_value)
        self.assertEqual(self.reset_value, part.reset_value)


class TestAttributePreRunPartSetupHooks(unittest.TestCase):
    def setUp(self):
        self.name = "ShutterPart"
        self.mri = "ML-SHUTTER-01"
        self.pre_run_value = "Open"
        self.reset_value = "Closed"

    def test_setup_sets_correct_hooks(self):
        part = AttributePreRunPart(
            self.name, self.mri, self.pre_run_value, self.reset_value
        )
        registrar_mock = Mock()
        part.setup(registrar_mock)

        # Check calls
        calls = [
            call(PreRunHook, part.on_pre_run),
            call((PauseHook, AbortHook, PostRunReadyHook), part.on_reset),
        ]
        registrar_mock.hook.assert_has_calls(calls)


class TestAttributePreRunPartWithDefaultNamePutMethods(unittest.TestCase):
    def setUp(self):
        # Create our part
        name = "ShutterPart"
        mri = "ML-SHUTTER-01"
        self.pre_run_value = "Open"
        self.reset_value = "Closed"
        self.part = AttributePreRunPart(name, mri, self.pre_run_value, self.reset_value)
        # Generate our mocks
        self.part.setup(Mock())
        self.context = Mock(name="context")
        self.child = Mock(name="child")
        self.context.block_view.return_value = self.child

    def test_puts_pre_run_value_to_child_on_pre_run(self):
        self.part.on_pre_run(self.context)
        self.child.shutter.put_value.assert_called_once_with(self.pre_run_value)

    def test_puts_reset_value_to_child_on_reset(self):
        self.part.on_reset(self.context)
        self.child.shutter.put_value.assert_called_once_with(self.reset_value)


class TestAttributePreRunPartWithNonDefaultNamePutMethods(unittest.TestCase):
    def setUp(self):
        # Create our part
        name = "AttributePart"
        mri = "ML-ATTR-01"
        self.pre_run_value = "Set"
        self.reset_value = "Reset"
        self.part = AttributePreRunPart(
            name, mri, self.pre_run_value, self.reset_value, attribute_name="togglePart"
        )
        # Generate our mocks
        self.part.setup(Mock())
        self.context = Mock(name="context")
        self.child = Mock(name="child")
        self.context.block_view.return_value = self.child

    def test_puts_pre_run_value_to_child_on_pre_run(self):
        self.part.on_pre_run(self.context)
        self.child.togglePart.put_value.assert_called_once_with(self.pre_run_value)

    def test_puts_reset_value_to_child_on_reset(self):
        self.part.on_reset(self.context)
        self.child.togglePart.put_value.assert_called_once_with(self.reset_value)
