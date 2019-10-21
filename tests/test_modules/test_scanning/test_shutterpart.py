import unittest
from mock import patch, Mock

from malcolm.modules.scanning.parts import ShutterPart


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
