import shutil
import tempfile
from typing import Dict

import pytest
from mock import MagicMock
from scanpointgenerator import (
    CompoundGenerator,
    LineGenerator,
    SquashingExcluder,
    StaticPointGenerator,
)

from malcolm.core import (
    AttributeModel,
    Context,
    NumberMeta,
    Part,
    PartRegistrar,
    Process,
    StringMeta,
)
from malcolm.modules.ADPandABlocks.blocks import panda_pulse_trigger_block
from malcolm.modules.ADPandABlocks.parts import PandAPulseTriggerPart
from malcolm.modules.builtin.controllers import BasicController, ManagerController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.demo.blocks import detector_block
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.parts import DetectorChildPart
from malcolm.modules.scanning.util import DetectorTable
from malcolm.testutil import ChildTestCase


class PulsePart(Part):
    mocks: Dict[str, MagicMock] = {}
    units: Dict[str, AttributeModel] = {}

    def setup(self, registrar: PartRegistrar) -> None:
        self.mocks = {}
        self.units = {}
        for suffix in ["step", "delay", "width", "pulses"]:
            # Add an attribute that will be set
            attr = NumberMeta("float64").create_attribute_model()
            mock = MagicMock(side_effect=attr.set_value)
            registrar.add_attribute_model(suffix, attr, mock)
            self.mocks[suffix] = mock
            if suffix != "pulses":
                # Add a units attribute that will be read
                units_attr = StringMeta().create_attribute_model("s")
                registrar.add_attribute_model(suffix + "Units", units_attr)
                self.units[suffix] = units_attr


class TestPandaPulseTriggerPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)

        # Create a fake PandA with a pulse block
        self.panda = ManagerController("PANDA", "/tmp")
        controller = BasicController("PANDA:PULSE3")
        self.pulse_part = PulsePart("part")
        controller.add_part(self.pulse_part)
        self.process.add_controller(controller)
        self.panda.add_part(
            ChildPart("PULSE3", "PANDA:PULSE3", initial_visibility=True, stateful=False)
        )
        self.process.add_controller(self.panda)

        # And the detector
        for c in detector_block("DET", config_dir="/tmp"):
            self.process.add_controller(c)

        # Make the child block holding panda and pmac mri
        self.child = self.create_child_block(
            panda_pulse_trigger_block,
            self.process,
            mri="SCAN:PULSE",
            panda="PANDA",
            detector="DET",
        )

        # And our part under test
        self.o = PandAPulseTriggerPart("detTrigger", "SCAN:PULSE")

        # Add in a scan block
        self.scan = RunnableController("SCAN", "/tmp")
        self.scan.add_part(DetectorChildPart("det", "DET", True))
        self.scan.add_part(self.o)
        self.process.add_controller(self.scan)

        # Now start the process off and tell the panda which sequencer tables
        # to use
        self.process.start()
        exports = ExportTable.from_rows(
            [
                ("PULSE3.width", "detTriggerWidth"),
                ("PULSE3.step", "detTriggerStep"),
                ("PULSE3.delay", "detTriggerDelay"),
                ("PULSE3.pulses", "detTriggerPulses"),
            ]
        )
        self.panda.set_exports(exports)
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self.process.stop(timeout=2)
        shutil.rmtree(self.tmpdir)

    def check_pulse_mocks(self, width, step, delay, pulses):
        self.pulse_part.mocks["width"].assert_called_once_with(pytest.approx(width))
        self.pulse_part.mocks["step"].assert_called_once_with(pytest.approx(step))
        self.pulse_part.mocks["delay"].assert_called_once_with(pytest.approx(delay))
        self.pulse_part.mocks["pulses"].assert_called_once_with(pulses)

    def test_configure_multiple_no_exposure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        detectors = DetectorTable.from_rows([[True, "det", "DET", 0.0, 5]])
        self.o.on_configure(self.context, generator, detectors)
        assert self.o.generator_duration == 1.0
        assert self.o.frames_per_step == 5
        # Detector would normally be configured by DetectorChildPart
        detector = self.process.block_view("DET")
        spg = StaticPointGenerator(5, axes=["det_frames_per_step"])
        ex = SquashingExcluder(axes=["det_frames_per_step", "x"])
        generatormultiplied = CompoundGenerator([ys, xs, spg], [ex], [], 0.2)
        detector.configure(generatormultiplied, self.tmpdir)
        self.o.on_post_configure()
        self.check_pulse_mocks(0.19899, 0.2, 0.000505, 5)

    def test_system(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        detectors = DetectorTable.from_rows([[True, "det", "DET", 0.0, 5]])
        b = self.scan.block_view()
        b.configure(generator, self.tmpdir, detectors=detectors)
        self.check_pulse_mocks(0.19899, 0.2, 0.000505, 5)

    def test_system_defined_exposure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        detectors = DetectorTable.from_rows([[True, "det", "DET", 0.1, 5]])
        b = self.scan.block_view()
        b.configure(generator, self.tmpdir, detectors=detectors)
        self.check_pulse_mocks(0.1, 0.2, 0.05, 5)
