import unittest

import pytest
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
            call("readoutTime", self.o.readout_time),
            call("frequencyAccuracy", self.o.frequency_accuracy),
            call("exposure", self.o.exposure),
        ]
        assert self.o.exposure.value == 0.0

    def test_validate_returns_min_duration_when_no_exposure_or_duration_given(
        self,
    ):
        tweak = self.o.on_validate(generator=make_generator(duration=0.0), exposure=0.0)
        assert tweak.parameter == "generator"
        assert tweak.value.duration == pytest.approx(0.0100005)

    def test_validate_returns_min_duration_when_given_exposure(
        self,
    ):
        tweak = self.o.on_validate(generator=make_generator(duration=0.0), exposure=0.5)
        assert tweak.parameter == "generator"
        assert tweak.value.duration == pytest.approx(0.500025)

    def test_validate_with_non_zero_duration_sets_maximum_possible_exposure_time(self):
        tweak = self.o.on_validate(generator=make_generator(duration=0.1))
        assert tweak.parameter == "exposure"
        assert tweak.value == pytest.approx(0.099995)

    def test_validate_raises_AssertionError_for_invalid_exposures(self):
        # Exposures below the minimum allowed and above the generator duration
        below_min_exposure = 0.005
        above_max_exposure = 1.01
        generator = make_generator(duration=1.0)

        self.assertRaises(
            AssertionError, self.o.on_validate, generator, exposure=below_min_exposure
        )
        self.assertRaises(
            AssertionError, self.o.on_validate, generator, exposure=above_max_exposure
        )

    def test_configure(self):
        self.o.on_configure(exposure=0.099995)
        assert self.o.exposure.value == 0.099995

    def test_report_status(self):
        info = self.o.on_report_status()
        assert info.readout_time == 0.0
        assert info.frequency_accuracy == 50
        assert info.min_exposure == 0.01
