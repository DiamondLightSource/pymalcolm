import numpy as np

from annotypes import Anno, Array
from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process, Part, TableMeta, PartRegistrar
from malcolm.modules.ADPandABlocks.blocks import pandablocks_pcomp_block
from malcolm.modules.ADPandABlocks.parts import PandABlocksPcompPart
from malcolm.modules.ADPandABlocks.util import SequencerTable, Trigger
from malcolm.modules.builtin.controllers import ManagerController, \
    BasicController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable
from malcolm.modules.pmac.infos import MotorInfo
from malcolm.testutil import ChildTestCase


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
        self.process.add_controller(self.panda)

        # Make the child block holding panda mri
        self.child = self.create_child_block(
            pandablocks_pcomp_block, self.process,
            mri="SCAN:PCOMP", panda="PANDA")

        # And our part under test
        self.o = PandABlocksPcompPart("pcomp", "SCAN:PCOMP", "x", "y")

        # Now start the process off and tell the panda which sequencer tables
        # to use
        self.process.start()
        exports = ExportTable.from_rows([
            ('SEQ1.table', 'seqTableA'),
            ('SEQ2.table', 'seqTableB')
        ])
        self.panda.set_exports(exports)

    def tearDown(self):
        self.process.stop(timeout=2)

    def make_part_info(self, x_pos=0.5, y_pos=0.0):
        part_info = dict(
            x=[MotorInfo(
                cs_axis="A",
                cs_port="CS1",
                acceleration=2.5,
                resolution=0.001,
                offset=0.0,
                max_velocity=1.0,
                current_position=x_pos,
                scannable="x",
                velocity_settle=0.0,
                units="mm"
            )],
            y=[MotorInfo(
                cs_axis="B",
                cs_port="CS1",
                acceleration=2.5,
                resolution=0.001,
                offset=0.0,
                max_velocity=1.0,
                current_position=y_pos,
                scannable="y",
                velocity_settle=0.0,
                units="mm"
            )],
        )
        return part_info

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.3, 4, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 8
        part_info = self.make_part_info()
        axes_to_move = ["x", "y"]
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, generator,
            axes_to_move)
        assert self.o.panda_mri == "PANDA"
        assert self.o.generator is generator
        assert self.o.loaded_up_to == completed_steps
        assert self.o.scan_up_to == completed_steps + steps_to_do
        self.o.post_configure(self.context)
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





