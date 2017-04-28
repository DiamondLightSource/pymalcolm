from mock import Mock, call, patch, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import call_with_params, Context, Process
from malcolm.modules.pmac.parts import PmacTrajectoryPart
from malcolm.modules.pmac.infos import MotorInfo
from malcolm.modules.pmac.blocks import pmac_trajectory_block
from malcolm.testutil import ChildTestCase


class TestPMACTrajectoryPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            pmac_trajectory_block, self.process, mri="PMAC:TRAJ",
            prefix="PV:PRE", statPrefix="PV:STAT")
        self.child.parts["i10"].attr.set_value(1705244)
        self.o = call_with_params(
            PmacTrajectoryPart, name="pmac", mri="PMAC:TRAJ")
        list(self.o.create_attributes())
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop()

    def resolutions_and_use_calls(self, useB=True):
        offset = [call('offsetA', 0.0)]
        resolution = [call('resolutionA', 0.001)]
        if useB:
            offset.append(call('offsetB', 0.0))
            resolution.append(call('resolutionB', 0.001))
        calls = offset + resolution + [
            call('useA', True),
            call('useB', useB),
            call('useC', False),
            call('useU', False),
            call('useV', False),
            call('useW', False),
            call('useX', False),
            call('useY', False),
            call('useZ', False)]
        return calls

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
            )]
        )
        return part_info

    def do_configure(self, axes_to_scan, completed_steps=0, x_pos=0.5,
                     y_pos=0.0, duration=1.0):
        part_info = self.make_part_info(x_pos, y_pos)
        steps_to_do = 3 * len(axes_to_scan)
        params = Mock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [], duration)
        params.generator.prepare()
        params.axesToMove = axes_to_scan
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)

    def test_validate(self):
        params = Mock()
        params.generator = CompoundGenerator([], [], [], 0.0102)
        params.axesToMove = ["x"]
        part_info = self.make_part_info()
        ret = self.o.validate(self.context, part_info, params)
        expected = 0.010166
        self.assertEqual(ret[0].value.duration, expected)

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_configure(self):
        self.do_configure(axes_to_scan=["x", "y"])
        assert self.child.mock_writes.mock_calls == [
            call('numPoints', 4000000),
            call('cs', 'CS1'),
        ] + self.resolutions_and_use_calls() + [
            call('pointsToBuild', 5),
            call('positionsA', [
                0.44617968749999998, 0.28499999999999998, 0.077499999999999958,
                -0.083679687500000072, -0.13750000000000007]),
            call('positionsB', [0.0, 0.0, 0.0, 0.0, 0.0]),
            call('timeArray', [207500, 207500, 207500, 207500, 207500]),
            call('userPrograms', [8, 8, 8, 8, 8]),
            call('velocityMode', [0, 0, 0, 0, 2]),
            call('buildProfile'),
            call('executeProfile'),
        ] + self.resolutions_and_use_calls() + [
            call('pointsToBuild', 16),
            call('positionsA', [
                -0.125, 0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.6375,
                0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375]),
            call('positionsB', [
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
                0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]),
            call('timeArray', [
                100000, 500000, 500000, 500000, 500000, 500000, 500000,
                200000, 200000, 500000, 500000, 500000, 500000, 500000,
                500000, 100000]),
            call('userPrograms', [
                3, 4, 3, 4, 3, 4, 2, 8, 3, 4, 3, 4, 3, 4, 2, 8]),
            call('velocityMode', [
                2, 0, 0, 0, 0, 0, 1, 0, 2, 0, 0, 0, 0, 0, 1, 3]),
            call('buildProfile')]

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_2_axis_move_to_start(self):
        self.do_configure(
            axes_to_scan=["x", "y"], x_pos=0.0, y_pos=0.2)
        assert self.child.mock_writes.mock_calls == [
            call('numPoints', 4000000),
            call('cs', 'CS1'),
        ] + self.resolutions_and_use_calls() + [
            call('pointsToBuild', 2),
            call('positionsA', [-0.068750000000000019, -0.13750000000000001]),
            call('positionsB', [0.10000000000000001, 0.0]),
            call('timeArray', [282843, 282842]),
            call('userPrograms', [8, 8]),
            call('velocityMode', [0, 2]),
            call('buildProfile'),
            call('executeProfile'),
        ] + self.resolutions_and_use_calls() + [
            call('pointsToBuild', ANY),
            call('positionsA', ANY),
            call('positionsB', ANY),
            call('timeArray', ANY),
            call('userPrograms', ANY),
            call('velocityMode', ANY),
            call('buildProfile')]

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.POINTS_PER_BUILD", 4)
    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_update_step(self):
        self.do_configure(axes_to_scan=["x", "y"])
        positionsA = self.child.mock_writes.call_args_list[-6][0][1]
        assert len(positionsA) == 11
        assert positionsA[-1] == 0.375
        assert self.o.end_index == 4
        assert len(self.o.completed_steps_lookup) == 11
        update_completed_steps = Mock()
        self.child.mock_writes.reset_mock()
        self.o.update_step(
            3, update_completed_steps, self.context.block_view("PMAC:TRAJ"))
        update_completed_steps.assert_called_once_with(1, self.o)
        assert not self.o.loading
        assert self.child.mock_writes.mock_calls == self.resolutions_and_use_calls() + [
            call('pointsToBuild', 5),
            call('positionsA', [
                0.25, 0.125, 0.0, -0.125, -0.1375]),
            call('positionsB', [
                0.1, 0.1, 0.1, 0.1, 0.1]),
            call('timeArray', [
                500000, 500000, 500000, 500000, 100000]),
            call('userPrograms', [
                4, 3, 4, 2, 8]),
            call('velocityMode', [
                0, 0, 0, 1, 3]),
            call('appendProfile')]

    def test_run(self):
        update = Mock()
        self.o.run(self.context, update)
        assert self.child.mock_writes.mock_calls == [call('executeProfile')]

    def test_multi_run(self):
        self.do_configure(axes_to_scan=["x"])
        self.assertEqual(self.o.completed_steps_lookup,
                         [0, 0, 1, 1, 2, 2, 3, 3])
        self.child.mock_writes.reset_mock()
        self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.6375)
        assert self.child.mock_writes.mock_calls == [
            call('numPoints', 4000000),
            call('cs', 'CS1'),
        ] + self.resolutions_and_use_calls(useB=False) + [
            call('pointsToBuild', 8),
            call('positionsA', [
                0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375]),
            call('timeArray', [
                100000, 500000, 500000, 500000, 500000, 500000, 500000,
                100000]),
            call('userPrograms', [3, 4, 3, 4, 3, 4, 2, 8]),
            call('velocityMode', [2, 0, 0, 0, 0, 0, 1, 3]),
            call('buildProfile')]

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_long_steps_lookup(self):
        self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.62506, duration=14.0)
        assert self.child.mock_writes.mock_calls[-6:] == [
            call('pointsToBuild', 14),
            call('positionsA',
                 [0.625, 0.5625, 0.5, 0.4375, 0.375, 0.3125, 0.25, 0.1875,
                  0.125, 0.0625, 0.0, -0.0625, -0.125,
                  -0.12506377551020409]),
            call('timeArray',
                 [7143, 3500000, 3500000, 3500000, 3500000, 3500000, 3500000,
                  3500000, 3500000, 3500000, 3500000, 3500000, 3500000,
                  7143]),
            call('userPrograms', [3, 0, 4, 0, 3, 0, 4, 0, 3, 0, 4, 0, 2, 8]),
            call('velocityMode', [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3]),
            call('buildProfile')]
        self.assertEqual(self.o.completed_steps_lookup,
                         [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6])

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           2.0)
    def test_long_move(self):
        self.do_configure(axes_to_scan=["x"], x_pos=-10.1375)
        assert self.child.mock_writes.mock_calls[13:18] == [
            call('pointsToBuild', 5),
            call('positionsA', [
                -8.2575000000000003, -6.1774999999999984, -4.0974999999999984,
                -2.0174999999999983, -0.1374999999999984]),
            call('timeArray', [2080000, 2080000, 2080000, 2080000, 2080000]),
            call('userPrograms', [8, 8, 8, 8, 8]),
            call('velocityMode', [0, 0, 0, 0, 2])]
