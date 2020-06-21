import os

import socket
import pytest
from mock import MagicMock, patch

from scanpointgenerator import LineGenerator, CompoundGenerator, \
    StaticPointGenerator

from malcolm.core import Context, Process, Part, TableMeta, PartRegistrar, \
    StringMeta
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.ADPandABlocks.blocks import panda_seq_trigger_block
from malcolm.modules.ADPandABlocks.parts import PandASeqTriggerPart
from malcolm.modules.ADPandABlocks.util import SequencerTable, Trigger, \
    DatasetPositionsTable
from malcolm.modules.ADPandABlocks.doublebuffer import SequencerRows, \
    DoubleBuffer, MIN_PULSE, TICK
from malcolm.modules.builtin.controllers import ManagerController, \
    BasicController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.pandablocks.util import PositionCapture
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator

from datetime import datetime
from numpy import isclose


class PositionsPart(Part):
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        pos_table = DatasetPositionsTable(
            name=["COUNTER1.VALUE", "INENC1.VAL", "INENC2.VAL"],
            value=[0.0] * 3,
            units=[""] * 3,
            # NOTE: x inverted from MRES below to simulate inversion of
            # encoder in the geobrick layer
            scale=[1.0, -0.001, 0.001],
            offset=[0.0, 0.0, 0.0],
            capture=[PositionCapture.NO] * 3,
            datasetName=["I0", 'x', 'y'],
            datasetType=[AttributeDatasetType.MONITOR,
                         AttributeDatasetType.POSITION,
                         AttributeDatasetType.POSITION]
        )
        attr = TableMeta.from_table(
            DatasetPositionsTable, "Sequencer Table",
            writeable=list(SequencerTable.call_types)
        ).create_attribute_model(pos_table)
        registrar.add_attribute_model("positions", attr)


class SequencerPart(Part):
    table_set = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        attr = TableMeta.from_table(
            SequencerTable, "Sequencer Table",
            writeable=list(SequencerTable.call_types)
        ).create_attribute_model()
        self.table_set = MagicMock(side_effect=attr.set_value)
        registrar.add_attribute_model("table", attr, self.table_set)
        for suff, val in (("a", "INENC1.VAL"),
                          ("b", "INENC2.VAL"),
                          ("c", "ZERO")):
            attr = StringMeta("Input").create_attribute_model(val)
            registrar.add_attribute_model("pos%s" % suff, attr)
        attr = StringMeta("Input").create_attribute_model("ZERO")
        registrar.add_attribute_model("bita", attr)


class GatePart(Part):
    enable_set = None

    def enable(self):
        self.enable_set()

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
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
                ChildPart("SEQ%d" % i, "PANDA:SEQ%d" % i,
                          initial_visibility=True, stateful=False))
        self.child_seq1 = self.process.get_controller("PANDA:SEQ1")
        self.child_seq2 = self.process.get_controller("PANDA:SEQ2")

        # And an srgate
        controller = BasicController("PANDA:SRGATE1")
        self.gate_part = GatePart("part")
        controller.add_part(self.gate_part)
        self.process.add_controller(controller)
        self.panda.add_part(
            ChildPart("SRGATE1", "PANDA:SRGATE1",
                      initial_visibility=True, stateful=False))
        self.process.add_controller(self.panda)

        # And the PMAC
        pmac_block = make_block_creator(
            os.path.join(os.path.dirname(__file__), "..", "test_pmac", "blah"),
            "test_pmac_manager_block.yaml")
        self.pmac = self.create_child_block(
            pmac_block, self.process, mri_prefix="PMAC",
            config_dir="/tmp")
        # These are the motors we are interested in
        self.child_x = self.process.get_controller("BL45P-ML-STAGE-01:X")
        self.child_y = self.process.get_controller("BL45P-ML-STAGE-01:Y")
        self.child_cs1 = self.process.get_controller("PMAC:CS1")
        # CS1 needs to have the right port otherwise we will error
        self.set_attributes(self.child_cs1, port="CS1")

        # Make the child block holding panda and pmac mri
        self.child = self.create_child_block(
            panda_seq_trigger_block, self.process,
            mri="SCAN:PCOMP", panda="PANDA", pmac="PMAC")

        # And our part under test
        self.o = PandASeqTriggerPart("pcomp", "SCAN:PCOMP")

        # Now start the process off and tell the panda which sequencer tables
        # to use
        self.process.start()
        exports = ExportTable.from_rows([
            ('SEQ1.table', 'seqTableA'),
            ('SEQ2.table', 'seqTableB'),
            ('SRGATE1.forceSet', 'seqSetEnable')
        ])
        self.panda.set_exports(exports)

    def tearDown(self):
        self.process.stop(timeout=2)

    def set_motor_attributes(
            self, x_pos=0.5, y_pos=0.0, units="mm",
            x_acceleration=2.5, y_acceleration=2.5,
            x_velocity=1.0, y_velocity=1.0):
        # create some parts to mock the motion controller and 2 axes in a CS
        self.set_attributes(
            self.child_x, cs="CS1,A",
            accelerationTime=x_velocity/x_acceleration, resolution=0.001,
            offset=0.0, maxVelocity=x_velocity, readback=x_pos,
            velocitySettle=0.0, units=units)
        self.set_attributes(
            self.child_y, cs="CS1,B",
            accelerationTime=y_velocity/y_acceleration, resolution=0.001,
            offset=0.0, maxVelocity=y_velocity, readback=y_pos,
            velocitySettle=0.0, units=units)

    @patch(
        'malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.DoubleBuffer',
        autospec=True)
    def test_configure_prepares_components(self, buffer_class):
        buffer_instance = buffer_class.return_value

        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        self.o.on_configure(self.context, completed_steps, steps_to_do, {},
                            generator, axes_to_move)

        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do

        # Other unit tests check that the sequencer rows used here are correct
        buffer_instance.configure.assert_called_once()

        self.gate_part.enable_set.assert_not_called()
        buffer_instance.run.assert_not_called()

        self.o.on_run(self.context)
        self.gate_part.enable_set.assert_called_once()
        buffer_instance.run.assert_called_once()

    @patch(
        'malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.DoubleBuffer',
        autospec=True)
    def get_sequencer_rows(self, generator, axes_to_move, buffer_class):
        """Helper method for comparing table values."""

        buffer_instance = buffer_class.return_value
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size

        self.o.on_configure(self.context, completed_steps, steps_to_do, {},
                            generator, axes_to_move)

        rows_gen = buffer_instance.configure.call_args[0][0]
        rows = SequencerRows()
        for rs in rows_gen:
            rows.extend(rs)

        return rows

    def test_configure_continuous(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move)
        # Triggers
        GT = Trigger.POSA_GT
        I = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        # Half how long to be blind for
        hb = 22500000
        expected = SequencerRows()
        expected.add_seq_entry(count=1, trigger=LT, position=50,
                               half_duration=hf, live=1, dead=0)
        expected.add_seq_entry(3, I, 0, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hb, 0, 1)
        expected.add_seq_entry(1, GT, -350, hf, 1, 0)
        expected.add_seq_entry(3, I, 0, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, 125000000, 0, 1)
        expected.add_seq_entry(0, I, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuple() == expected.as_tuple()

    def test_configure_motion_controller_trigger(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        self.set_motor_attributes()
        self.set_attributes(self.child, rowTrigger="Motion Controller")
        self.set_attributes(self.child_seq1, bita="TTLIN1.VAL")
        self.set_attributes(self.child_seq2, bita="TTLIN1.VAL")
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move)
        # Triggers
        B0 = Trigger.BITA_0
        B1 = Trigger.BITA_1
        I = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        expected = SequencerRows()
        expected.add_seq_entry(count=1, trigger=B1, position=0,
                               half_duration=hf, live=1, dead=0)
        expected.add_seq_entry(3, I, 0, hf, 1, 0)
        expected.add_seq_entry(1, B0, 0, 1250, 0, 1)
        expected.add_seq_entry(1, B1, 0, hf, 1, 0)
        expected.add_seq_entry(3, I, 0, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, 125000000, 0, 1)
        expected.add_seq_entry(0, I, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuple() == expected.as_tuple()

    def test_configure_stepped(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0, continuous=False)
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        with self.assertRaises(AssertionError):
            self.o.on_configure(self.context, completed_steps, steps_to_do, {},
                                generator, axes_to_move)

    def test_acquire_scan(self):
        generator = CompoundGenerator(
            [StaticPointGenerator(size=5)], [], [], 1.0)
        generator.prepare()

        seq_rows = self.get_sequencer_rows(generator, [])
        # Triggers
        I = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        expected = SequencerRows()
        expected.add_seq_entry(count=5, trigger=I, position=0,
                               half_duration=hf, live=1, dead=0)
        expected.add_seq_entry(1, I, 0, 125000000, 0, 1)
        expected.add_seq_entry(0, I, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuple() == expected.as_tuple()

    def test_configure_single_point_multi_frames(self):
        # This test uses PCAP to generate a static point test.
        # The test moves the motors to a new position and then generates
        # 5 triggers at that position

        xs = LineGenerator("x", "mm", 0.0, 0.0, 5, alternate=True)
        ys = LineGenerator("y", "mm", 1.0, 1.0, 1)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()

        # TODO: This should probably be removed as it appears to check a property
        # of CompoundGenerator.
        steps_to_do = 5
        self.assertEqual(steps_to_do, generator.size)

        completed_steps = 0
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        self.o.on_configure(self.context, completed_steps, steps_to_do, {},
                            generator, axes_to_move)

    def test_configure_pcomp_row_trigger_with_single_point_rows(self):
        x_steps, y_steps = 1, 5
        xs = LineGenerator("x", "mm", 0.0, 0.5, x_steps, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 4, y_steps)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move)
        # Triggers
        GT = Trigger.POSA_GT
        LT = Trigger.POSA_LT
        I = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        # Half blind
        hb = 75000000
        expected = SequencerRows()
        expected.add_seq_entry(count=1, trigger=LT, position=0,
                               half_duration=hf, live=1, dead=0)
        expected.add_seq_entry(1, I, 0, hb, 0, 1)
        expected.add_seq_entry(1, GT, -500, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hb, 0, 1)
        expected.add_seq_entry(1, LT, 0, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hb, 0, 1)
        expected.add_seq_entry(1, GT, -500, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hb, 0, 1)
        expected.add_seq_entry(1, LT, 0, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, 125000000, 0, 1)
        expected.add_seq_entry(0, I, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuple() == expected.as_tuple()

    def test_configure_with_delay_after(self):
        # a test to show that delay_after inserts a "loop_back" turnaround
        delay = 1.0
        x_steps, y_steps = 3, 2
        xs = LineGenerator("x", "mm", 0.0, 0.5, x_steps, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, y_steps)
        generator = CompoundGenerator([ys, xs], [], [], 1.0, delay_after=delay)
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move)
        # Triggers
        GT = Trigger.POSA_GT
        I = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        # Half how long to be blind for a single point
        hfb = 55625000
        # Half how long to be blind for end of row
        hrb = 56500000
        expected = SequencerRows()
        expected.add_seq_entry(count=1, trigger=LT, position=125,
                               half_duration=hf, live=1, dead=0)
        expected.add_seq_entry(1, I, 0, hfb, 0, 1)
        expected.add_seq_entry(1, LT, -125, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hfb, 0, 1)
        expected.add_seq_entry(1, LT, -375, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hrb, 0, 1)
        expected.add_seq_entry(1, GT, -625, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hfb, 0, 1)
        expected.add_seq_entry(1, GT, -375, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, hfb, 0, 1)
        expected.add_seq_entry(1, GT, -125, hf, 1, 0)
        expected.add_seq_entry(1, I, 0, 125000000, 0, 1)
        expected.add_seq_entry(0, I, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuple() == expected.as_tuple()

    def test_configure_long_pcomp_row_trigger(self):
        # Test that the configure() time is reasonable
        if 'diamond.ac.uk' not in socket.gethostname():
            pytest.skip("performance test only")

        x_steps, y_steps = 4000, 1000
        xs = LineGenerator("x", "mm", 0.0, 10, x_steps, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 8, y_steps)
        generator = CompoundGenerator([ys, xs], [], [], .005)
        generator.prepare()
        completed_steps = 0
        steps_to_do = x_steps * y_steps
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        start = datetime.now()
        self.o.on_configure(self.context, completed_steps, steps_to_do, {},
                            generator, axes_to_move)
        elapsed = datetime.now() - start
        assert elapsed.total_seconds() < 3.0


class TestDoubleBuffer(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)

        # Make 2 sequencers we can prod
        self.seq_parts = {}
        for i in (1, 2):
            controller = BasicController("TEST:SEQ%d" % i)
            self.seq_parts[i] = SequencerPart("part")
            controller.add_part(self.seq_parts[i])
            self.process.add_controller(controller)

        # # Now start the process off
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=2)

    @staticmethod
    def rows_generator():
        triggers = (Trigger.BITA_0, Trigger.IMMEDIATE, Trigger.POSB_GT)

        for i in range(1, 4):
            rows = SequencerRows()
            rows.add_seq_entry(count=i, trigger=triggers[i % 3], position=10*i,
                               half_duration=1000*i, live=i % 2, dead=(i+1) % 2,
                               trim=100*i)
            yield rows

    def test_table_rows_are_set_correctly_on_configure(self):
        seq1_block = self.context.block_view("TEST:SEQ1")
        seq2_block = self.context.block_view("TEST:SEQ2")
        db = DoubleBuffer(seq1_block.table, seq2_block.table)

        db.configure(self.rows_generator())

        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]

        assert table.repeats == [1, 2, 3]
        assert table.trigger == [Trigger.IMMEDIATE, Trigger.POSB_GT,
                                 Trigger.BITA_0]
        assert table.position == [10, 20, 30]
        assert table.time1 == [1000, 2000, 3000]
        assert table.outa1 == [1, 0, 1]  # Live
        assert table.outb1 == [0, 1, 0]  # Dead
        assert table.outc1 == table.outd1 == table.oute1 == table.outf1 == \
            [0, 0, 0]
        assert table.time2 == [900, 1800, 2700]
        assert table.outa2 == table.outb2 == table.outc2 == table.outd2 == \
            table.oute2 == table.outf2 == [0, 0, 0]


class TestSequencerRows(ChildTestCase):

    def test_initial_rows_parameter_for_constructor(self):
        initial_list = [[1, Trigger.POSA_GT, 100, 3000, 1, 0, 0, 0, 0, 0,
                         2700, 0, 0, 0, 0, 0, 0],
                        [3, Trigger.BITA_0, 300, 2000, 0, 1, 0, 0, 0, 0,
                         1900, 0, 0, 0, 0, 0, 0]]

        seq_rows = SequencerRows(initial_list)
        total_ticks = (3000 + 2700) + 3 * (2000 + 1900)
        assert isclose(seq_rows.duration, total_ticks * TICK)
        assert len(seq_rows) == 2

        table = seq_rows.get_table()
        assert table.repeats == [1, 3]
        assert table.trigger == [Trigger.POSA_GT, Trigger.BITA_0]
        assert table.position == [100, 300]
        assert table.time1 == [3000, 2000]
        assert table.outa1 == [1, 0]  # Live
        assert table.outb1 == [0, 1]  # Dead
        assert table.outc1 == table.outd1 == table.oute1 == table.outf1 == \
            [0, 0]
        assert table.time2 == [2700, 1900]
        assert table.outa2 == table.outb2 == table.outc2 == table.outd2 == \
            table.oute2 == table.outf2 == [0, 0]

    def test_add_seq_entry(self):
        seq_rows = SequencerRows()
        # Check defaults:
        seq_rows.add_seq_entry()
        seq_rows.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)

        total_ticks = (MIN_PULSE * 2) + 4 * (1000 + 950)
        assert isclose(seq_rows.duration, total_ticks * TICK)
        assert len(seq_rows) == 2

        table = seq_rows.get_table()
        assert table.repeats == [1, 4]
        assert table.trigger == [Trigger.IMMEDIATE, Trigger.POSB_LT]
        assert table.position == [0, 400]
        assert table.time1 == [MIN_PULSE, 1000]
        assert table.outa1 == [0, 0]  # Live
        assert table.outb1 == [0, 1]  # Dead
        assert table.outc1 == table.outd1 == table.oute1 == table.outf1 == \
            [0, 0]
        assert table.time2 == [MIN_PULSE, 950]
        assert table.outa2 == table.outb2 == table.outc2 == table.outd2 == \
            table.oute2 == table.outf2 == [0, 0]

    def test_extend(self):
        seq_rows = SequencerRows()
        seq_rows.add_seq_entry()
        seq_rows2 = SequencerRows()
        seq_rows2.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        seq_rows.extend(seq_rows2)

        total_ticks = (MIN_PULSE * 2) + 4 * (1000 + 950)
        assert isclose(seq_rows.duration, total_ticks * TICK)
        assert len(seq_rows) == 2

        table = seq_rows.get_table()
        assert table.repeats == [1, 4]
        assert table.trigger == [Trigger.IMMEDIATE, Trigger.POSB_LT]
        assert table.position == [0, 400]
        assert table.time1 == [MIN_PULSE, 1000]
        assert table.outa1 == [0, 0]  # Live
        assert table.outb1 == [0, 1]  # Dead
        assert table.outc1 == table.outd1 == table.oute1 == table.outf1 == \
            [0, 0]
        assert table.time2 == [MIN_PULSE, 950]
        assert table.outa2 == table.outb2 == table.outc2 == table.outd2 == \
            table.oute2 == table.outf2 == [0, 0]

    def test_as_tuple(self):
        initial_list = [[1, Trigger.POSA_GT, 100, 3000, 1, 0, 0, 0, 0, 0,
                         2700, 0, 0, 0, 0, 0, 0],
                        [3, Trigger.BITA_0, 300, 2000, 0, 1, 0, 0, 0, 0,
                         1900, 0, 0, 0, 0, 0, 0]]

        expected = tuple(tuple(row) for row in initial_list)

        seq_rows = SequencerRows(initial_list)
        assert seq_rows.as_tuple() == expected
