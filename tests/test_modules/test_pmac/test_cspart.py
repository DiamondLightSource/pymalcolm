from mock import call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import CSPart
from malcolm.modules.pmac.infos import MotorInfo
from malcolm.modules.pmac.blocks import cs_block
from malcolm.testutil import ChildTestCase


class TestCSPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            cs_block, self.process, mri="PMAC:CS1",
            prefix="PV:PRE")
        self.set_attributes(self.child, port="CS1")
        self.o = CSPart(name="pmac", mri="PMAC:CS1")
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def make_part_info(self, x_pos=0.5, y_pos=0.0):
        part_info = dict(
            xpart=[MotorInfo(
                cs_axis="A",
                cs_port="CS1",
                acceleration=2.5,
                resolution=0.001,
                offset=0.0,
                max_velocity=1.0,
                current_position=x_pos,
                scannable="x",
                velocity_settle=0.0,
            )],
            ypart=[MotorInfo(
                cs_axis="B",
                cs_port="CS1",
                acceleration=2.5,
                resolution=0.001,
                offset=0.0,
                max_velocity=1.0,
                current_position=y_pos,
                scannable="y",
                velocity_settle=0.0,
            )],
        )
        return part_info

    def do_configure(self, axes_to_scan, completed_steps=0, x_pos=0.5,
                     y_pos=0.0, duration=1.0):
        part_info = self.make_part_info(x_pos, y_pos)
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], duration)
        generator.prepare()
        self.o.configure(
            self.context, completed_steps, part_info,
            generator, axes_to_scan)

    def test_configure(self):
        # Pretend to respond on demand values before they are actually set
        self.set_attributes(self.child, demandA=-0.1375, demandB=0.0)
        self.do_configure(axes_to_scan=["x", "y"])
        assert self.child.handled_requests.mock_calls == [
            call.put('deferMoves', True),
            call.put('csMoveTime', 0),
            call.put('demandA', -0.1375),
            call.put('demandB', 0.0),
            call.put('deferMoves', False)
        ]

    def test_abort(self):
        self.o.abort(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('abort'),
        ]

    def test_reset(self):
        self.o.reset(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('abort'),
        ]

