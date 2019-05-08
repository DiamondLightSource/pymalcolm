import os

import numpy as np

from annotypes import Anno, Array
from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process, Part, TableMeta, PartRegistrar
from malcolm.modules.ADPandABlocks.blocks import panda_pcomp_block
from malcolm.modules.ADPandABlocks.parts import PandABlocksPcompPart
from malcolm.modules.ADPandABlocks.util import SequencerTable, Trigger
from malcolm.modules.builtin.controllers import ManagerController, \
    BasicController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.pmac.infos import MotorInfo
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator


class SequencerPart(Part):
    table_set = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        table = TableMeta.from_table(
            SequencerTable, "Sequencer Table",
            writeable=list(SequencerTable.call_types)
        ).create_attribute_model()
        self.table_set = MagicMock(side_effect=table.set_value)
        registrar.add_attribute_model("table", table, self.table_set)


class GatePart(Part):
    enable_set = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.enable_set = MagicMock()
        registrar.add_method_model(MagicMock, "forceSet")


class TestPcompPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)

        # Create a fake PandA
        self.panda = ManagerController("PANDA", "/tmp")

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
        # And an srgate
        controller = BasicController("PANDA:SRGATE1")
        controller.add_part(GatePart("part"))
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
            panda_pcomp_block, self.process,
            mri="SCAN:PCOMP", panda="PANDA", pmac="PMAC")

        # And our part under test
        self.o = PandABlocksPcompPart("pcomp", "SCAN:PCOMP", "x", "y")

        # Now start the process off and tell the panda which sequencer tables
        # to use
        self.process.start()
        exports = ExportTable.from_rows([
            ('SEQ1.table', 'seqTableA'),
            ('SEQ2.table', 'seqTableB'),
            ('SRGATE1.forceSet', 'seqTableEnable')
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

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 8
        self.set_motor_attributes()
        axes_to_move = ["x", "y"]
        self.o.configure(
            self.context, completed_steps, steps_to_do, {}, generator,
            axes_to_move)
        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do
        # Triggers
        GT = Trigger.POSA_GT
        I = Trigger.IMMEDIATE
        LT = Trigger.POSA_LT
        # Half a frame
        t = 62500000
        # How long to be blind for
        b = 44999999
        self.seq_parts[1].table_set.assert_called_once()
        table = self.seq_parts[1].table_set.call_args[0][0]
        assert table.repeats == [1, 3, 1, 1, 3, 1]
        assert table.trigger == [GT, I, I, LT, I, I]
        assert table.position == [-50, 0, 0, 350, 0, 0]
        assert table.time1 == [t, t, 1, t, t, 1]
        assert table.outa1 == [1, 1, 0, 1, 1, 0]  # Live
        assert table.outb1 == [1, 1, 0, 1, 1, 0]  # Gate
        assert table.outc1 == [0, 1, 1, 0, 1, 1]  # PCAP
        assert table.outd1 == [0, 0, 0, 0, 0, 0]
        assert table.oute1 == [0, 0, 0, 0, 0, 0]
        assert table.outf1 == [0, 0, 0, 0, 0, 0]
        assert table.time2 == [t, t, b, t, t, 1]
        assert table.outa2 == [0, 0, 0, 0, 0, 0]  # Live
        assert table.outb2 == [1, 1, 0, 1, 1, 0]  # Gate
        assert table.outc2 == [0, 0, 0, 0, 0, 0]  # PCAP
        assert table.outd2 == [0, 0, 0, 0, 0, 0]
        assert table.oute2 == [0, 0, 0, 0, 0, 0]
        assert table.outf2 == [0, 0, 0, 0, 0, 0]





