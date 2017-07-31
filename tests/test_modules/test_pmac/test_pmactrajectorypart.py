from mock import Mock, call, patch, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator
import pytest

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
        list(self.o.create_attribute_models())
        self.process.start()

    #def tearDown(self):
    #    del self.context
    #    self.process.stop(timeout=1)

    def resolutions_and_use_call(self, useB=True):
        offset = [call.put('offsetA', 0.0)]
        resolution = [call.put('resolutionA', 0.001)]
        if useB:
            offset.append(call.put('offsetB', 0.0))
            resolution.append(call.put('resolutionB', 0.001))
        call.puts = offset + resolution + [
            call.put('useA', True),
            call.put('useB', useB),
            call.put('useC', False),
            call.put('useU', False),
            call.put('useV', False),
            call.put('useW', False),
            call.put('useX', False),
            call.put('useY', False),
            call.put('useZ', False)]
        return call.puts

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
        assert ret[0].value.duration == expected

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_configure(self):
        self.do_configure(axes_to_scan=["x", "y"])
        assert self.child.handled_requests.mock_calls == [
            call.put('numPoints', 4000000),
            call.put('cs', 'CS1'),
        ] + self.resolutions_and_use_call() + [
            call.put('pointsToBuild', 5),
            call.put('positionsA', pytest.approx([
                0.4461796875, 0.285, 0.0775, -0.0836796875, -0.1375])),
            call.put('positionsB', [0.0, 0.0, 0.0, 0.0, 0.0]),
            call.put('timeArray', [207500, 207500, 207500, 207500, 207500]),
            call.put('userPrograms', [8, 8, 8, 8, 8]),
            call.put('velocityMode', [0, 0, 0, 0, 2]),
            call.post('buildProfile'),
            call.post('executeProfile'),
        ] + self.resolutions_and_use_call() + [
            call.put('pointsToBuild', 16),
            call.put('positionsA', pytest.approx([
                -0.125, 0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.6375,
                0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375])),
            call.put('positionsB', pytest.approx([
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
                0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])),
            call.put('timeArray', [
                100000, 500000, 500000, 500000, 500000, 500000, 500000,
                200000, 200000, 500000, 500000, 500000, 500000, 500000,
                500000, 100000]),
            call.put('userPrograms', [
                3, 4, 3, 4, 3, 4, 2, 8, 3, 4, 3, 4, 3, 4, 2, 8]),
            call.put('velocityMode', [
                2, 0, 0, 0, 0, 0, 1, 0, 2, 0, 0, 0, 0, 0, 1, 3]),
            call.post('buildProfile')]
        assert self.o.completed_steps_lookup == [
                0, 0, 1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 6, 6]

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_2_axis_move_to_start(self):
        self.do_configure(
            axes_to_scan=["x", "y"], x_pos=0.0, y_pos=0.2)
        assert self.child.handled_requests.mock_calls == [
            call.put('numPoints', 4000000),
            call.put('cs', 'CS1'),
        ] + self.resolutions_and_use_call() + [
            call.put('pointsToBuild', 2),
            call.put('positionsA', pytest.approx([-0.06875, -0.1375])),
            call.put('positionsB', pytest.approx([0.1, 0.0])),
            call.put('timeArray', [282843, 282842]),
            call.put('userPrograms', [8, 8]),
            call.put('velocityMode', [0, 2]),
            call.post('buildProfile'),
            call.post('executeProfile'),
        ] + self.resolutions_and_use_call() + [
            call.put('pointsToBuild', ANY),
            call.put('positionsA', ANY),
            call.put('positionsB', ANY),
            call.put('timeArray', ANY),
            call.put('userPrograms', ANY),
            call.put('velocityMode', ANY),
            call.post('buildProfile')]

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.PROFILE_POINTS", 4)
    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_update_step(self):
        self.do_configure(axes_to_scan=["x", "y"], x_pos=0.0, y_pos=0.2)
        positionsA = self.child.handled_requests.put.call_args_list[-5][0][1]
        assert len(positionsA) == 4
        assert positionsA[-1] == 0.25
        assert self.o.end_index == 2
        assert len(self.o.completed_steps_lookup) == 5
        assert len(self.o.profile["time_array"]) == 1
        update_completed_steps = Mock()
        self.child.handled_requests.reset_mock()
        self.o.update_step(
            3, update_completed_steps, self.context.block_view("PMAC:TRAJ"))
        update_completed_steps.assert_called_once_with(1, self.o)
        assert not self.o.loading
        assert self.child.handled_requests.mock_calls == self.resolutions_and_use_call() + [
            call.put('pointsToBuild', 4),
            call.put('positionsA', pytest.approx([
                0.375, 0.5, 0.625, 0.6375])),
            call.put('positionsB', pytest.approx([
                0.0, 0.0, 0.0, 0.05])),
            call.put('timeArray', [
                500000, 500000, 500000, 200000]),
            call.put('userPrograms', [
                3, 4, 2, 8]),
            call.put('velocityMode', [
                0, 0, 1, 0]),
            call.post('appendProfile')]
        assert self.o.end_index == 3
        assert len(self.o.completed_steps_lookup) == 9
        assert len(self.o.profile["time_array"]) == 1

    def test_run(self):
        update = Mock()
        self.o.run(self.context, update)
        assert self.child.handled_requests.mock_calls == [
            call.post('executeProfile')]

    def test_multi_run(self):
        self.do_configure(axes_to_scan=["x"])
        assert self.o.completed_steps_lookup == (
                         [0, 0, 1, 1, 2, 2, 3, 3])
        self.child.handled_requests.reset_mock()
        self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.6375)
        assert self.child.handled_requests.mock_calls == [
            call.put('numPoints', 4000000),
            call.put('cs', 'CS1'),
        ] + self.resolutions_and_use_call(useB=False) + [
            call.put('pointsToBuild', 8),
            call.put('positionsA', pytest.approx([
                0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375])),
            call.put('timeArray', [
                100000, 500000, 500000, 500000, 500000, 500000, 500000,
                100000]),
            call.put('userPrograms', [3, 4, 3, 4, 3, 4, 2, 8]),
            call.put('velocityMode', [2, 0, 0, 0, 0, 0, 1, 3]),
            call.post('buildProfile')]

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           0.2)
    def test_long_steps_lookup(self):
        self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.62506, duration=14.0)
        assert self.child.handled_requests.mock_calls[-6:] == [
            call.put('pointsToBuild', 14),
            call.put('positionsA', pytest.approx([
                0.625, 0.5625, 0.5, 0.4375, 0.375, 0.3125, 0.25, 0.1875,
                0.125, 0.0625, 0.0, -0.0625, -0.125,
                -0.12506377551020409])),
            call.put('timeArray',
                 [7143, 3500000, 3500000, 3500000, 3500000, 3500000, 3500000,
                  3500000, 3500000, 3500000, 3500000, 3500000, 3500000,
                  7143]),
            call.put('userPrograms', [3, 0, 4, 0, 3, 0, 4, 0, 3, 0, 4, 0, 2, 8]),
            call.put('velocityMode', [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3]),
            call.post('buildProfile')]
        assert self.o.completed_steps_lookup == (
                         [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6])

    @patch("malcolm.modules.pmac.parts.pmactrajectorypart.INTERPOLATE_INTERVAL",
           2.0)
    def test_long_move(self):
        self.do_configure(axes_to_scan=["x"], x_pos=-10.1375)
        assert self.child.handled_requests.mock_calls[13:18] == [
            call.put('pointsToBuild', 5),
            call.put('positionsA', pytest.approx([
                -8.2575, -6.1775, -4.0975, -2.0175, -0.1375])),
            call.put('timeArray', [2080000, 2080000, 2080000, 2080000, 2080000]),
            call.put('userPrograms', [8, 8, 8, 8, 8]),
            call.put('velocityMode', [0, 0, 0, 0, 2])]
