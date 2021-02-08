import os
from datetime import datetime

import pytest
from mock import MagicMock
from scanpointgenerator import CompoundGenerator, LineGenerator, StaticPointGenerator

from malcolm.core import Context, Part, PartRegistrar, Process, StringMeta, TableMeta
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.ADPandABlocks.blocks import panda_seq_trigger_block
from malcolm.modules.ADPandABlocks.parts import PandASeqTriggerPart
from malcolm.modules.ADPandABlocks.util import (
    DatasetPositionsTable,
    SequencerTable,
    Trigger,
)
from malcolm.modules.builtin.controllers import BasicController, ManagerController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.pandablocks.util import PositionCapture
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator


class PositionsPart(Part):
    def setup(self, registrar: PartRegistrar) -> None:
        pos_table = DatasetPositionsTable(
            name=["COUNTER1.VALUE", "INENC1.VAL", "INENC2.VAL"],
            value=[0.0] * 3,
            units=[""] * 3,
            # NOTE: x inverted from MRES below to simulate inversion of
            # encoder in the geobrick layer
            scale=[1.0, -0.001, 0.001],
            offset=[0.0, 0.0, 0.0],
            capture=[PositionCapture.MIN_MAX_MEAN] * 3,
            datasetName=["I0", "x", "y"],
            datasetType=[
                AttributeDatasetType.MONITOR,
                AttributeDatasetType.POSITION,
                AttributeDatasetType.POSITION,
            ],
        )
        attr = TableMeta.from_table(
            DatasetPositionsTable,
            "Sequencer Table",
            writeable=list(SequencerTable.call_types),
        ).create_attribute_model(pos_table)
        registrar.add_attribute_model("positions", attr)


class SequencerPart(Part):
    table_set = None

    def setup(self, registrar: PartRegistrar) -> None:
        attr = TableMeta.from_table(
            SequencerTable, "Sequencer Table", writeable=list(SequencerTable.call_types)
        ).create_attribute_model()
        self.table_set = MagicMock(side_effect=attr.set_value)
        registrar.add_attribute_model("table", attr, self.table_set)
        for suff, val in (("a", "INENC1.VAL"), ("b", "INENC2.VAL"), ("c", "ZERO")):
            attr = StringMeta("Input").create_attribute_model(val)
            registrar.add_attribute_model("pos%s" % suff, attr)
        attr = StringMeta("Input").create_attribute_model("ZERO")
        registrar.add_attribute_model("bita", attr)


class GatePart(Part):
    enable_set = None

    def enable(self):
        self.enable_set()

    def setup(self, registrar: PartRegistrar) -> None:
        self.enable_set = MagicMock()
        registrar.add_method_model(self.enable, "forceSet")


class TestPandaSeqTriggerPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)

        # Create a fake PandA
        self.panda = ManagerController("PANDA", "/tmp")
        self.busses = PositionsPart("busses")
        self.panda.add_part(self.busses)

        # Make 2 sequencers we can prod
        self.seq_parts = {}
        for i in (1, 2):
            controller = BasicController("PANDA:SEQ%d" % i)
            self.seq_parts[i] = SequencerPart("part")
            controller.add_part(self.seq_parts[i])
            self.process.add_controller(controller)
            self.panda.add_part(
                ChildPart(
                    "SEQ%d" % i,
                    "PANDA:SEQ%d" % i,
                    initial_visibility=True,
                    stateful=False,
                )
            )
        self.child_seq1 = self.process.get_controller("PANDA:SEQ1")
        self.child_seq2 = self.process.get_controller("PANDA:SEQ2")

        # And an srgate
        controller = BasicController("PANDA:SRGATE1")
        self.gate_part = GatePart("part")
        controller.add_part(self.gate_part)
        self.process.add_controller(controller)
        self.panda.add_part(
            ChildPart(
                "SRGATE1", "PANDA:SRGATE1", initial_visibility=True, stateful=False
            )
        )
        self.process.add_controller(self.panda)

        # And the PMAC
        pmac_block = make_block_creator(
            os.path.join(os.path.dirname(__file__), "..", "test_pmac", "blah"),
            "test_pmac_manager_block.yaml",
        )
        self.pmac = self.create_child_block(
            pmac_block, self.process, mri_prefix="PMAC", config_dir="/tmp"
        )
        # These are the motors we are interested in
        self.child_x = self.process.get_controller("BL45P-ML-STAGE-01:X")
        self.child_y = self.process.get_controller("BL45P-ML-STAGE-01:Y")
        self.child_cs1 = self.process.get_controller("PMAC:CS1")
        # CS1 needs to have the right port otherwise we will error
        self.set_attributes(self.child_cs1, port="CS1")

        # Make the child block holding panda and pmac mri
        self.child = self.create_child_block(
            panda_seq_trigger_block,
            self.process,
            mri="SCAN:PCOMP",
            panda="PANDA",
            pmac="PMAC",
        )

        # And our part under test
        self.o = PandASeqTriggerPart("pcomp", "SCAN:PCOMP")

        # Now start the process off and tell the panda which sequencer tables
        # to use
        self.process.start()
        exports = ExportTable.from_rows(
            [
                ("SEQ1.table", "seqTableA"),
                ("SEQ2.table", "seqTableB"),
                ("SRGATE1.forceSet", "seqSetEnable"),
            ]
        )
        self.panda.set_exports(exports)

    def tearDown(self):
        self.process.stop(timeout=2)

    def set_motor_attributes(
        self,
        x_pos=0.5,
        y_pos=0.0,
        units="mm",
        x_acceleration=2.5,
        y_acceleration=2.5,
        x_velocity=1.0,
        y_velocity=1.0,
    ):
        # create some parts to mock the motion controller and 2 axes in a CS
        self.set_attributes(
            self.child_x,
            cs="CS1,A",
            accelerationTime=x_velocity / x_acceleration,
            resolution=0.001,
            offset=0.0,
            maxVelocity=x_velocity,
            readback=x_pos,
            velocitySettle=0.0,
            units=units,
        )
        self.set_attributes(
            self.child_y,
            cs="CS1,B",
            accelerationTime=y_velocity / y_acceleration,
            resolution=0.001,
            offset=0.0,
            maxVelocity=y_velocity,
            readback=y_pos,
            velocitySettle=0.0,
            units=units,
        )

    def test_configure_continuous(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 8
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )
        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do
        # Triggers
        GT = Trigger.POSA_GT
        IT = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        # Half how long to be blind for
        hb = 22500000
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        assert table.repeats == [1, 3, 1, 1, 3, 1]
        assert table.trigger == [LT, IT, IT, GT, IT, IT]
        assert table.position == [50, 0, 0, -350, 0, 0]
        assert table.time1 == [hf, hf, hb, hf, hf, 125000000]
        assert table.outa1 == [1, 1, 0, 1, 1, 0]  # Live
        assert table.outb1 == [0, 0, 1, 0, 0, 1]  # Dead
        assert (
            table.outc1
            == table.outd1
            == table.oute1
            == table.outf1
            == [0, 0, 0, 0, 0, 0]
        )
        assert table.time2 == [hf, hf, hb, hf, hf, 125000000]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0, 0, 0, 0, 0]
        )
        # Check we didn't press the gate part
        self.gate_part.enable_set.assert_not_called()
        self.o.on_run(self.context)
        # Check we pressed the gate part
        self.gate_part.enable_set.assert_called_once()

    def test_configure_motion_controller_trigger(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 8
        self.set_motor_attributes()
        self.set_attributes(self.child, rowTrigger="Motion Controller")
        self.set_attributes(self.child_seq1, bita="TTLIN1.VAL")
        self.set_attributes(self.child_seq2, bita="TTLIN1.VAL")
        axes_to_move = ["x", "y"]
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )
        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do
        # Triggers
        B0 = Trigger.BITA_0
        B1 = Trigger.BITA_1
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        assert table.repeats == [1, 3, 1, 1, 3, 1]
        assert table.trigger == [B1, IT, B0, B1, IT, IT]
        assert table.time1 == [hf, hf, 1250, hf, hf, 125000000]
        assert table.position == [0, 0, 0, 0, 0, 0]
        assert table.outa1 == [1, 1, 0, 1, 1, 0]  # Live
        assert table.outb1 == [0, 0, 1, 0, 0, 1]  # Dead
        assert (
            table.outc1
            == table.outd1
            == table.oute1
            == table.outf1
            == [0, 0, 0, 0, 0, 0]
        )
        assert table.time2 == [hf, hf, 1250, hf, hf, 125000000]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0, 0, 0, 0, 0]
        )
        # Check we didn't press the gate part
        self.gate_part.enable_set.assert_not_called()
        self.o.on_run(self.context)
        # Check we pressed the gate part
        self.gate_part.enable_set.assert_called_once()

    def test_configure_stepped(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0, continuous=False)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 8
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]
        with self.assertRaises(AssertionError):
            self.o.on_configure(
                self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
            )

    def test_acquire_scan(self):
        generator = CompoundGenerator([StaticPointGenerator(size=5)], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 5
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, []
        )
        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do
        # Triggers
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        assert table.repeats == [5, 1]
        assert table.trigger == [IT, IT]
        assert table.position == [0, 0]
        assert table.time1 == [hf, 125000000]
        assert table.outa1 == [1, 0]  # Live
        assert table.outb1 == [0, 1]  # Dead
        assert table.outc1 == table.outd1 == table.oute1 == table.outf1 == [0, 0]
        assert table.time2 == [hf, 125000000]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0]
        )
        # Check we didn't press the gate part
        self.gate_part.enable_set.assert_not_called()

    def test_configure_single_point_multi_frames(self):
        # This test uses PCAP to generate a static point test.
        # The test moves the motors to a new position and then generates
        # 5 triggers at that position

        xs = LineGenerator("x", "mm", 0.0, 0.0, 5, alternate=True)
        ys = LineGenerator("y", "mm", 1.0, 1.0, 1)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()

        steps_to_do = 5
        self.assertEqual(steps_to_do, generator.size)

        completed_steps = 0
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )

    def test_configure_pcomp_row_trigger_with_single_point_rows(self):
        x_steps, y_steps = 1, 5
        xs = LineGenerator("x", "mm", 0.0, 0.5, x_steps, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 4, y_steps)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = x_steps * y_steps
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )

        # Triggers
        GT = Trigger.POSA_GT
        LT = Trigger.POSA_LT
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        # Half blind
        hb = 75000000
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        assert table.repeats == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        assert table.trigger == [LT, IT, GT, IT, LT, IT, GT, IT, LT, IT]
        assert table.time1 == [hf, hb, hf, hb, hf, hb, hf, hb, hf, 125000000]
        assert table.position == [0, 0, -500, 0, 0, 0, -500, 0, 0, 0]
        assert table.outa1 == [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]  # Live
        assert table.outb1 == [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]  # Dead
        assert (
            table.outc1
            == table.outd1
            == table.oute1
            == table.outf1
            == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        assert table.time2 == [hf, hb, hf, hb, hf, hb, hf, hb, hf, 125000000]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        # Check we didn't press the gate part
        self.gate_part.enable_set.assert_not_called()
        self.o.on_run(self.context)
        # Check we pressed the gate part
        self.gate_part.enable_set.assert_called_once()

    def test_configure_with_delay_after(self):
        # a test to show that delay_after inserts a "loop_back" turnaround
        delay = 1.0
        x_steps, y_steps = 3, 2
        xs = LineGenerator("x", "mm", 0.0, 0.5, x_steps, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, y_steps)
        generator = CompoundGenerator([ys, xs], [], [], 1.0, delay_after=delay)
        generator.prepare()
        completed_steps = 0
        steps_to_do = x_steps * y_steps
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )
        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do
        # Triggers
        GT = Trigger.POSA_GT
        IT = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        # Half how long to be blind for a single point
        hfb = 55625000
        # Half how long to be blind for end of row
        hrb = 56500000
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        assert table.repeats == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        assert table.trigger == [LT, IT, LT, IT, LT, IT, GT, IT, GT, IT, GT, IT]
        assert table.position == [125, 0, -125, 0, -375, 0, -625, 0, -375, 0, -125, 0]
        assert table.time1 == [
            hf,
            hfb,
            hf,
            hfb,
            hf,
            hrb,
            hf,
            hfb,
            hf,
            hfb,
            hf,
            125000000,
        ]
        assert table.outa1 == [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]  # Live
        assert table.outb1 == [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]  # Dead
        assert (
            table.outc1
            == table.outd1
            == table.oute1
            == table.outf1
            == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        assert table.time2 == [
            hf,
            hfb,
            hf,
            hfb,
            hf,
            hrb,
            hf,
            hfb,
            hf,
            hfb,
            hf,
            125000000,
        ]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        # Check we didn't press the gate part
        self.gate_part.enable_set.assert_not_called()
        self.o.on_run(self.context)
        # Check we pressed the gate part
        self.gate_part.enable_set.assert_called_once()

    def test_configure_long_pcomp_row_trigger(self):
        # Skip on GitHub Actions and GitLab CI
        if "CI" in os.environ:
            pytest.skip("performance test only")

        self.set_motor_attributes(
            0,
            0,
            "mm",
            x_velocity=300,
            y_velocity=300,
            x_acceleration=30,
            y_acceleration=30,
        )
        x_steps, y_steps = 4000, 1000
        xs = LineGenerator("x", "mm", 0.0, 10, x_steps, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 8, y_steps)
        generator = CompoundGenerator([ys, xs], [], [], 0.005)
        generator.prepare()
        completed_steps = 0
        steps_to_do = x_steps * y_steps
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        start = datetime.now()
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )
        elapsed = datetime.now() - start
        assert elapsed.total_seconds() < 3.0
