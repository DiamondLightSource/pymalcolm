import os
import shutil
from datetime import datetime

import pytest
from mock import MagicMock, Mock, call, patch
from numpy import isclose
from scanpointgenerator import CompoundGenerator, LineGenerator, StaticPointGenerator

from malcolm.core import (
    BooleanMeta,
    Context,
    NumberMeta,
    Part,
    PartRegistrar,
    Process,
    StringMeta,
    TableMeta,
)
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.ADPandABlocks.blocks import panda_seq_trigger_block
from malcolm.modules.ADPandABlocks.doublebuffer import (
    MAX_REPEATS,
    MIN_PULSE,
    MIN_TABLE_DURATION,
    SEQ_TABLE_SWITCH_DELAY,
    TICK,
    DoubleBuffer,
    SequencerRows,
)
from malcolm.modules.ADPandABlocks.parts import PandASeqTriggerPart
from malcolm.modules.ADPandABlocks.util import (
    DatasetPositionsTable,
    SequencerTable,
    Trigger,
)
from malcolm.modules.builtin.controllers import BasicController, ManagerController
from malcolm.modules.builtin.defines import tmp_dir
from malcolm.modules.builtin.hooks import ResetHook
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.pandablocks.util import PositionCapture
from malcolm.modules.scanning.hooks import (
    AbortHook,
    ConfigureHook,
    PauseHook,
    PostRunArmedHook,
    ReportStatusHook,
    RunHook,
    SeekHook,
)
from malcolm.modules.scanning.infos import MotionTrigger
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

        attr = BooleanMeta("Active", (), True).create_attribute_model(False)
        registrar.add_attribute_model("active", attr, attr.set_value)

        attr = NumberMeta("int16", "repeats", writeable=True).create_attribute_model(1)
        registrar.add_attribute_model("repeats", attr, writeable_func=attr.set_value)


class GatePart(Part):
    enable_set = None
    seq_reset = None

    def enable(self):
        self.enable_set()

    def reset(self):
        self.seq_reset()

    def setup(self, registrar: PartRegistrar) -> None:
        self.enable_set = MagicMock()
        registrar.add_method_model(self.enable, "forceSet")
        self.seq_reset = MagicMock()
        registrar.add_method_model(self.reset, "forceReset")


class TestPandaSeqTriggerPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)

        # Create a fake PandA
        self.panda = ManagerController("PANDA", "/tmp", use_git=False)
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
        self.config_dir = tmp_dir("config_dir")
        self.pmac = self.create_child_block(
            pmac_block,
            self.process,
            mri_prefix="PMAC",
            config_dir=self.config_dir.value,
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
                ("SRGATE1.forceReset", "seqReset"),
            ]
        )
        self.panda.set_exports(exports)

    def tearDown(self):
        self.process.stop(timeout=2)
        shutil.rmtree(self.config_dir.value)

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

    # Patch the super setup() method so we only get desired calls
    @patch("malcolm.modules.builtin.parts.ChildPart.setup")
    def test_setup(self, mocked_super_setup):
        mock_registrar = Mock(name="mock_registrar")
        call_list = [
            call(ReportStatusHook, self.o.on_report_status),
            call((ConfigureHook, SeekHook), self.o.on_configure),
            call(RunHook, self.o.on_run),
            call(ResetHook, self.o.on_reset),
            call((AbortHook, PauseHook), self.o.on_abort),
            call(PostRunArmedHook, self.o.post_inner_scan),
        ]

        self.o.setup(mock_registrar)

        mocked_super_setup.assert_called_once_with(mock_registrar)
        mock_registrar.hook.assert_has_calls(call_list, any_order=True)

    @patch(
        "malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.DoubleBuffer",
        autospec=True,
    )
    def test_configure_and_run_prepare_components(self, buffer_class):
        buffer_instance = buffer_class.return_value
        buffer_instance.run.return_value = []

        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )

        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do

        # Other unit tests check that the sequencer rows used here are correct
        buffer_instance.configure.assert_called_once()

        self.gate_part.enable_set.assert_not_called()
        buffer_instance.run.assert_not_called()

        # The SRGate should only be enabled by on_pre_run() here.
        self.o.on_pre_run(self.context)
        self.o.on_run(self.context)
        self.gate_part.enable_set.assert_called_once()
        buffer_instance.run.assert_called_once()

    @patch(
        "malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.DoubleBuffer",
        autospec=True,
    )
    def test_configure_and_run_prepare_no_axes(self, buffer_class):
        buffer_instance = buffer_class.return_value
        buffer_instance.run.return_value = []

        generator = CompoundGenerator([StaticPointGenerator(size=1)], [], [], 1.0)
        generator.prepare()

        completed_steps = 0
        steps_to_do = generator.size

        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, ""
        )

        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do

        buffer_instance.configure.assert_called_once()

        self.gate_part.enable_set.assert_not_called()
        buffer_instance.run.assert_not_called()

        # The SRGate should only be enabled by on_run() here.
        self.o.on_pre_run(self.context)
        self.o.on_run(self.context)
        self.gate_part.enable_set.assert_called_once()
        buffer_instance.run.assert_called_once()

    @patch(
        "malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.PandASeqTriggerPart"
        ".on_abort",
        autospec=True,
    )
    def test_reset_triggers_abort(self, abort_method):
        abort_method.assert_not_called()
        self.o.on_reset(self.context)
        abort_method.assert_called_once()

    @patch(
        "malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.DoubleBuffer.clean_up",
        autospec=True,
    )
    def test_abort_cleans_up_correctly(self, db_clean_up_method):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        db_clean_up_method.assert_not_called()
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )
        db_clean_up_method.assert_called_once()

        self.gate_part.seq_reset.assert_not_called()
        self.o.on_abort(self.context)
        self.gate_part.seq_reset.assert_called_once()
        assert 2 == db_clean_up_method.call_count

    def test_abort_does_not_throw_exception_if_no_seq_reset_exported(self):
        original_exports = self.panda.exports.value.rows()
        exports = ExportTable.from_rows(
            [row for row in original_exports if row[1] != "seqReset"]
        )
        self.panda.set_exports(exports)

        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )
        self.o.on_abort(self.context)

    @patch(
        "malcolm.modules.ADPandABlocks.parts.pandaseqtriggerpart.DoubleBuffer",
        autospec=True,
    )
    def get_sequencer_rows(self, generator, axes_to_move, buffer_class, steps=None):
        """Helper method for comparing table values."""

        buffer_instance = buffer_class.return_value
        generator.prepare()
        completed_steps = 0
        steps_to_do = steps if steps is not None else generator.size

        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
        )

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
        IT = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        # Half how long to be blind for
        hb = 22500000
        expected = SequencerRows()
        expected.add_seq_entry(
            count=1, trigger=LT, position=50, half_duration=hf, live=1, dead=0
        )
        expected.add_seq_entry(3, IT, 0, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hb, 0, 1)
        expected.add_seq_entry(1, GT, -350, hf, 1, 0)
        expected.add_seq_entry(3, IT, 0, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

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
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        expected = SequencerRows()
        expected.add_seq_entry(
            count=1, trigger=B1, position=0, half_duration=hf, live=1, dead=0
        )
        expected.add_seq_entry(3, IT, 0, hf, 1, 0)
        expected.add_seq_entry(1, B0, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(1, B1, 0, hf, 1, 0)
        expected.add_seq_entry(3, IT, 0, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

    # AssertionError is thrown as inputs are not are not set for SEQ bitA.
    def test_configure_assert_stepped(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0, continuous=False)
        generator.prepare()
        completed_steps = 0
        steps_to_do = generator.size
        self.set_motor_attributes()
        self.set_attributes(self.child, rowTrigger="Motion Controller")
        axes_to_move = ["x", "y"]

        with self.assertRaises(AssertionError):
            self.o.on_configure(
                self.context, completed_steps, steps_to_do, {}, generator, axes_to_move
            )

    def test_configure_stepped(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4)
        ys = LineGenerator("y", "mm", 0.0, 0.2, 3)
        generator = CompoundGenerator([ys, xs], [], [], 1.0, continuous=False)
        generator.prepare()
        self.set_motor_attributes()
        self.set_attributes(self.child, rowTrigger="Motion Controller")
        self.set_attributes(self.child_seq1, bita="TTLIN1.VAL")
        self.set_attributes(self.child_seq2, bita="TTLIN1.VAL")
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move)
        # Triggers
        B0 = Trigger.BITA_0
        B1 = Trigger.BITA_1
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        expected = SequencerRows()
        for i in range(11):
            expected.add_seq_entry(1, B1, 0, hf, 1, 0)
            expected.add_seq_entry(1, B0, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(1, B1, 0, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

    def test_acquire_scan(self):
        generator = CompoundGenerator([StaticPointGenerator(size=5)], [], [], 1.0)
        generator.prepare()

        seq_rows = self.get_sequencer_rows(generator, [])
        # Triggers
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        expected = SequencerRows()
        expected.add_seq_entry(
            count=5, trigger=IT, position=0, half_duration=hf, live=1, dead=0
        )
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

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
        IT = Trigger.IMMEDIATE
        # Half a frame
        hf = 62500000
        # Half blind
        hb = 75000000
        expected = SequencerRows()
        expected.add_seq_entry(
            count=1, trigger=LT, position=0, half_duration=hf, live=1, dead=0
        )
        expected.add_seq_entry(1, IT, 0, hb, 0, 1)
        expected.add_seq_entry(1, GT, -500, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hb, 0, 1)
        expected.add_seq_entry(1, LT, 0, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hb, 0, 1)
        expected.add_seq_entry(1, GT, -500, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hb, 0, 1)
        expected.add_seq_entry(1, LT, 0, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

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
        IT = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        # Half how long to be blind for a single point
        hfb = 55625000
        # Half how long to be blind for end of row
        hrb = 56500000
        expected = SequencerRows()
        expected.add_seq_entry(
            count=1, trigger=LT, position=125, half_duration=hf, live=1, dead=0
        )
        expected.add_seq_entry(1, IT, 0, hfb, 0, 1)
        expected.add_seq_entry(1, LT, -125, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hfb, 0, 1)
        expected.add_seq_entry(1, LT, -375, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hrb, 0, 1)
        expected.add_seq_entry(1, GT, -625, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hfb, 0, 1)
        expected.add_seq_entry(1, GT, -375, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, hfb, 0, 1)
        expected.add_seq_entry(1, GT, -125, hf, 1, 0)
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

    def test_configure_with_zero_points(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move, steps=0)
        # Triggers
        IT = Trigger.IMMEDIATE
        expected = SequencerRows()
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

    def test_configure_with_one_point(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]

        seq_rows = self.get_sequencer_rows(generator, axes_to_move, steps=1)
        # Triggers
        IT = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        hf = 62500000
        expected = SequencerRows()
        expected.add_seq_entry(
            count=1, trigger=LT, position=50, half_duration=hf, live=1, dead=0
        )
        expected.add_seq_entry(1, IT, 0, MIN_PULSE, 0, 1)
        expected.add_seq_entry(0, IT, 0, MIN_PULSE, 0, 0)

        assert seq_rows.as_tuples() == expected.as_tuples()

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

    def test_on_report_status_doing_pcomp(self):
        mock_context = MagicMock(name="context_mock")
        mock_child = MagicMock(name="child_mock")
        mock_child.rowTrigger.value = "Position Compare"
        mock_context.block_view.return_value = mock_child

        info = self.o.on_report_status(mock_context)

        assert info.trigger == MotionTrigger.NONE

    def test_on_report_status_not_doing_pcomp_is_row_gate(self):
        mock_context = MagicMock(name="context_mock")
        mock_child = MagicMock(name="child_mock")
        mock_child.rowTrigger.value = "Motion Controller"
        mock_context.block_view.return_value = mock_child

        info = self.o.on_report_status(mock_context)

        assert info.trigger == MotionTrigger.ROW_GATE


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

        # Now start the process off
        self.process.start()

        self.seq1_block = self.context.block_view("TEST:SEQ1")
        self.seq2_block = self.context.block_view("TEST:SEQ2")
        self.db = DoubleBuffer(self.context, self.seq1_block, self.seq2_block)

    def tearDown(self):
        self.process.stop(timeout=2)

    @staticmethod
    def assert_rows_equal_table(rows, table):
        """Compare sequencer table output to SequencerRows object.

        This converts a sequencer table to the same format as produced by the
        SequencerRows.as_tuples() method.
        """
        t = table
        table_params = [
            t.repeats,
            t.trigger,
            t.position,
            t.time1,
            t.outa1,
            t.outb1,
            t.outc1,
            t.outd1,
            t.oute1,
            t.outf1,
            t.time2,
            t.outa2,
            t.outb2,
            t.outc2,
            t.outd2,
            t.oute2,
            t.outf2,
        ]

        # Transpose and convert to tuples
        table_tuple = tuple(zip(*table_params))
        assert table_tuple == rows.as_tuples()

    @staticmethod
    def rows_generator(rows_arr):
        for rows in rows_arr:
            yield rows

    def test_tables_are_set_correctly_on_configure(self):
        min_ticks = int(MIN_TABLE_DURATION / TICK)

        rows1 = SequencerRows()  # Just over half min duration
        rows1.add_seq_entry(count=2, half_duration=min_ticks // 8 + 1000)

        rows2 = SequencerRows()  # Just over minimum duration
        rows2.add_seq_entry(count=1, half_duration=min_ticks // 8 + 1000)
        rows2.add_seq_entry(count=3, half_duration=min_ticks // 8 + 1000)

        extra = SequencerRows()  # Extra tables are ignored for configure()
        extra.add_seq_entry(count=2, half_duration=min_ticks // 8 + 1000)
        extra.add_seq_entry(count=2, half_duration=min_ticks // 8 + 1000)
        self.db.configure(self.rows_generator([rows1, rows1, rows2, extra]))

        # Check to ensure repeats is set correctly
        for table in self.db._table_map.values():
            assert table.repeats.value == 1

        self.seq_parts[1].table_set.assert_called_once()
        table1 = self.seq_parts[1].table_set.call_args[0][0]
        expected1 = SequencerRows()
        expected1.add_seq_entry(count=2, half_duration=min_ticks // 8 + 1000)
        expected1.add_seq_entry(count=1, half_duration=min_ticks // 8 + 1000)
        expected1.add_seq_entry(
            count=1, half_duration=min_ticks // 8 + 1000, trim=SEQ_TABLE_SWITCH_DELAY
        )
        self.assert_rows_equal_table(expected1, table1)

        self.seq_parts[2].table_set.assert_called_once()
        table2 = self.seq_parts[2].table_set.call_args[0][0]
        expected2 = SequencerRows()
        expected2.add_seq_entry(count=1, half_duration=min_ticks // 8 + 1000)
        expected2.add_seq_entry(count=2, half_duration=min_ticks // 8 + 1000)
        expected2.add_seq_entry(
            count=1, half_duration=min_ticks // 8 + 1000, trim=SEQ_TABLE_SWITCH_DELAY
        )
        self.assert_rows_equal_table(expected2, table2)

    @staticmethod
    def get_sequencer_rows(position=0):
        min_ticks = int(MIN_TABLE_DURATION / TICK)

        rows = SequencerRows()
        rows.add_seq_entry(
            count=2, half_duration=min_ticks // 4 + 100, position=position
        )

        expected = SequencerRows()
        expected.add_seq_entry(
            count=1, half_duration=min_ticks // 4 + 100, position=position
        )
        expected.add_seq_entry(
            count=1,
            half_duration=min_ticks // 4 + 100,
            position=position,
            trim=SEQ_TABLE_SWITCH_DELAY,
        )
        return rows, expected

    def test_tables_update_correctly_on_active_status(self):
        rows_list = []
        exp_list = []
        for i in range(5):  # Generate list of identifiable tables
            generated, expected = self.get_sequencer_rows(i)
            rows_list.append(generated)
            exp_list.append(expected)

        self.db.configure(self.rows_generator(rows_list))

        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        self.assert_rows_equal_table(exp_list[0], table)

        self.seq_parts[2].table_set.assert_called_once()
        table2 = self.seq_parts[2].table_set.call_args[0][0]
        self.assert_rows_equal_table(exp_list[1], table2)

        self.seq_parts[1].table_set.reset_mock()
        self.seq_parts[2].table_set.reset_mock()

        futures = self.db.run()

        self.seq_parts[1].table_set.assert_not_called()
        self.seq_parts[2].table_set.assert_not_called()

        self.seq1_block.active.put_value_async(True)
        self.context.sleep(0)
        self.seq_parts[1].table_set.assert_not_called()
        self.seq_parts[2].table_set.assert_not_called()

        self.seq2_block.active.put_value_async(True)
        self.seq1_block.active.put_value_async(False)
        self.context.sleep(0)
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        self.assert_rows_equal_table(exp_list[2], table)
        self.seq_parts[2].table_set.assert_not_called()
        self.seq_parts[1].table_set.reset_mock()

        self.seq2_block.active.put_value_async(False)
        self.seq1_block.active.put_value_async(True)
        self.context.sleep(0)
        self.seq_parts[1].table_set.assert_not_called()
        self.seq_parts[2].table_set.assert_called_once()
        table2 = self.seq_parts[2].table_set.call_args[0][0]
        self.assert_rows_equal_table(exp_list[3], table2)
        self.seq_parts[2].table_set.reset_mock()

        self.seq2_block.active.put_value_async(True)
        self.seq1_block.active.put_value_async(False)
        self.context.sleep(0)
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        self.assert_rows_equal_table(exp_list[4], table)
        self.seq_parts[2].table_set.assert_not_called()
        self.seq_parts[1].table_set.reset_mock()

        self.seq2_block.active.put_value_async(False)
        self.seq1_block.active.put_value_async(True)
        self.context.sleep(0)
        self.seq_parts[1].table_set.assert_not_called()
        self.seq_parts[2].table_set.assert_not_called()

        with pytest.raises(Exception):
            for future in futures:
                self.context.unsubscribe(future)


class TestSequencerRows(ChildTestCase):
    def test_get_table(self):
        initial_list = [
            (1, Trigger.POSA_GT, 100, 3000, 1, 0, 0, 0, 0, 0, 2700, 0, 0, 0, 0, 0, 0),
            (3, Trigger.BITA_0, 300, 2000, 0, 1, 0, 0, 0, 0, 1900, 0, 0, 0, 0, 0, 0),
        ]

        total_ticks = (3000 + 2700) + 3 * (2000 + 1900)

        seq_rows = SequencerRows.from_tuple_list(initial_list)
        seq_rows.add_seq_entry()
        seq_rows.add_seq_entry(4, Trigger.POSA_GT, 400, 1000, 0, 1, 50)
        seq_rows.add_seq_entry(
            (2 * MAX_REPEATS) + 20, Trigger.BITA_0, 300, 200, 1, 0, 100
        )

        total_ticks += (
            (MIN_PULSE * 2) + (4 * (1000 + 950)) + (2 * MAX_REPEATS + 20) * (200 + 100)
        )
        assert isclose(seq_rows.duration, total_ticks * TICK)
        assert len(seq_rows) == 7

        table = seq_rows.get_table()
        GT = Trigger.POSA_GT
        IT = Trigger.IMMEDIATE
        B0 = Trigger.BITA_0
        assert table.repeats == [1, 3, 1, 4, MAX_REPEATS, MAX_REPEATS, 20]
        assert table.trigger == [GT, B0, IT, GT, B0, B0, B0]
        assert table.position == [100, 300, 0, 400, 300, 300, 300]
        assert table.time1 == [3000, 2000, MIN_PULSE, 1000, 200, 200, 200]
        assert table.outa1 == [1, 0, 0, 0, 1, 1, 1]  # Live
        assert table.outb1 == [0, 1, 0, 1, 0, 0, 0]  # Dead
        assert (
            table.outc1
            == table.outd1
            == table.oute1
            == table.outf1
            == [0, 0, 0, 0, 0, 0, 0]
        )
        assert table.time2 == [2700, 1900, MIN_PULSE, 950, 100, 100, 100]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0, 0, 0, 0, 0, 0]
        )

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
        assert table.outc1 == table.outd1 == table.oute1 == table.outf1 == [0, 0]
        assert table.time2 == [MIN_PULSE, 950]
        assert (
            table.outa2
            == table.outb2
            == table.outc2
            == table.outd2
            == table.oute2
            == table.outf2
            == [0, 0]
        )

    def test_as_tuples(self):
        initial_list = [
            (1, Trigger.POSA_GT, 100, 3000, 1, 0, 0, 0, 0, 0, 2700, 0, 0, 0, 0, 0, 0),
            (3, Trigger.BITA_0, 300, 2000, 0, 1, 0, 0, 0, 0, 1900, 0, 0, 0, 0, 0, 0),
        ]
        seq_rows = SequencerRows.from_tuple_list(initial_list)

        expected = tuple(initial_list)
        assert seq_rows.as_tuples() == expected

    def test_split_below_max_table_size(self):
        seq_rows = SequencerRows()
        seq_rows.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        seq_rows.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)

        expected = SequencerRows()
        expected.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        expected.add_seq_entry(2, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        expected.add_seq_entry(
            1, Trigger.BITA_0, 300, 2000, 1, 0, 100 + SEQ_TABLE_SWITCH_DELAY
        )

        remainder = seq_rows.split(100)

        assert seq_rows.as_tuples() == expected.as_tuples()
        assert remainder.as_tuples() == SequencerRows().as_tuples()

    def test_split_above_max_table_size(self):
        seq_rows = SequencerRows()
        seq_rows.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        seq_rows.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        seq_rows.add_seq_entry(2, Trigger.POSB_GT, 300, 2000, 0, 1, 100)
        seq_rows.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)

        expected = SequencerRows()
        expected.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        expected.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        expected.add_seq_entry(
            1, Trigger.POSB_GT, 300, 2000, 0, 1, 100 + SEQ_TABLE_SWITCH_DELAY
        )

        exp_rem = SequencerRows()
        exp_rem.add_seq_entry(1, Trigger.POSB_GT, 300, 2000, 0, 1, 100)
        exp_rem.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)

        remainder = seq_rows.split(3)

        assert seq_rows.as_tuples() == expected.as_tuples()
        assert remainder.as_tuples() == exp_rem.as_tuples()

    def test_split_with_final_row_zero_repeat(self):
        seq_rows = SequencerRows()
        seq_rows.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        seq_rows.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        seq_rows.add_seq_entry(0, Trigger.IMMEDIATE, 300, 2000, 0, 1, 100)

        expected = SequencerRows()  # End of scan - no switch delay
        expected.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        expected.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        expected.add_seq_entry(0, Trigger.IMMEDIATE, 300, 2000, 0, 1, 100)

        remainder = seq_rows.split(3)

        assert seq_rows.as_tuples() == expected.as_tuples()
        assert remainder.as_tuples() == SequencerRows().as_tuples()

    def test_split_with_final_row_one_repeat(self):
        seq_rows = SequencerRows()
        seq_rows.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        seq_rows.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        seq_rows.add_seq_entry(1, Trigger.POSB_LT, 300, 2000, 0, 1, 100)

        expected = SequencerRows()
        expected.add_seq_entry(4, Trigger.POSB_LT, 400, 1000, 0, 1, 50)
        expected.add_seq_entry(3, Trigger.BITA_0, 300, 2000, 1, 0, 100)
        expected.add_seq_entry(
            1, Trigger.POSB_LT, 300, 2000, 0, 1, 100 + SEQ_TABLE_SWITCH_DELAY
        )

        remainder = seq_rows.split(3)

        assert seq_rows.as_tuples() == expected.as_tuples()
        assert remainder.as_tuples() == SequencerRows().as_tuples()
