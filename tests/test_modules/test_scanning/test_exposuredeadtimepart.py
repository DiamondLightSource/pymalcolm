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
            call("readoutTime", self.o.readout_time, self.o.readout_time.set_value),
            call(
                "frequencyAccuracy",
                self.o.frequency_accuracy,
                self.o.frequency_accuracy.set_value,
            ),
            call("exposure", self.o.exposure),
        ]
        assert self.o.exposure.value == 0.0

    def test_validate_sets_exposure_to_minimum_value_when_below(self):
        tweak = self.o.on_validate(
            generator=make_generator(duration=0.1), exposure=0.001
        )
        assert tweak.parameter == "exposure"
        assert tweak.value == 0.01

    def test_validate_returns_min_exposure_and_duration_when_neither_given(
        self,
    ):
        tweaks = self.o.on_validate(
            generator=make_generator(duration=0.0), exposure=0.0
        )
        assert tweaks[0].parameter == "generator"
        assert tweaks[0].value.duration == pytest.approx(0.0100005)
        assert tweaks[1].parameter == "exposure"
        assert tweaks[1].value == 0.01

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

    def test_configure(self):
        self.o.on_configure(exposure=0.099995)
        assert self.o.exposure.value == 0.099995

    def test_report_status(self):
        info = self.o.on_report_status()
        assert info.readout_time == 0.0
        assert info.frequency_accuracy == 50
        assert info.min_exposure == 0.01