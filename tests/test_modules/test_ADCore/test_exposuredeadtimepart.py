import unittest

from mock import MagicMock, call
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import PartRegistrar
from malcolm.modules.scanning.parts import ExposureDeadtimePart


def make_generator(duration):
    line1 = LineGenerator("y", "mm", 0, 2, 3)
    line2 = LineGenerator("x", "mm", 0, 2, 2)
    compound = CompoundGenerator([line1, line2], [], [], duration=duration)
    return compound


class TestExposureDeadtimePart(unittest.TestCase):
    def setUp(self):
        self.o = ExposureDeadtimePart(name="n", min_exposure=0.01)

    def test_init(self):
        registrar = MagicMock(spec=PartRegistrar)
        self.o.setup(registrar)
        assert registrar.add_attribute_model.mock_calls == [
            call("readoutTime", self.o.readout_time, self.o.readout_time.set_value),
            call(
                "frequencyAccuracy",
                self.o.frequency_accuracy,
                self.o.frequency_accuracy.set_value,
            ),
            call("exposure", self.o.exposure),
        ]
        assert self.o.exposure.value == 0.0

    def test_validate_exposure_too_fast(self):
        tweak = self.o.on_validate(
            generator=make_generator(duration=0.1), exposure=0.001
        )
        assert tweak.parameter == "exposure"
        assert tweak.value == 0.01

    def test_validate_no_duration(self):
        with self.assertRaises(AssertionError) as cm:
            self.o.on_validate(generator=make_generator(duration=0.0))
        assert (
            str(cm.exception)
            == "Duration 0.0 for generator must be >0 to signify constant exposure"
        )

    def test_good_validate(self):
        self.o.on_validate(generator=make_generator(duration=0.1))

    def test_configure(self):
        self.o.on_configure(exposure=0.099995)
        assert self.o.exposure.value == 0.099995

    def test_report_status(self):
        info = self.o.on_report_status()
        assert info.readout_time == 0.0
        assert info.frequency_accuracy == 50
        assert info.min_exposure == 0.01
