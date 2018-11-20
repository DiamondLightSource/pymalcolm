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
        self.o = PandABlocksPcompPart("pcomp", "SCAN:PCOMP")

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
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 6
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

    def test_run(self):
        self.o.registrar = MagicMock()
        self.o.run(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('start')]
        assert self.o.registrar.report.called_once
        assert self.o.registrar.report.call_args[0][0].steps == 0

    def test_abort(self):
        self.o.abort(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('stop')]
