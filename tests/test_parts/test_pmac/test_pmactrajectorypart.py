import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
import pytest
from mock import MagicMock, call, patch, ANY

Mock = MagicMock

from malcolm.core import call_with_params
from malcolm.parts.pmac import PmacTrajectoryPart
from malcolm.infos.pmac import MotorInfo
from scanpointgenerator import LineGenerator, CompoundGenerator


class TestPMACTrajectoryPart(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.o = call_with_params(
            PmacTrajectoryPart, name="pmac", mri="TST-PMAC")
        list(self.o.create_attributes())
        self.context = MagicMock()
        self.child = self.context.block_view.return_value
        self.child.i10 = 1705244

    def resolutions_and_use(self, useB=True):
        expected = dict(
            resolutionA=0.001,
            offsetA=0.0,
            useA=True,
            useB=useB,
            useC=False,
            useU=False,
            useV=False,
            useW=False,
            useX=False,
            useY=False,
            useZ=False)
        if useB:
            expected.update(dict(
                resolutionB=0.001,
                offsetB=0.0))
        return expected

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

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_configure(self):
        self.do_configure(axes_to_scan=["x", "y"])
        assert self.context.mock_calls == [
            call.unsubscribe_all(),
            call.block_view('TST-PMAC'),
            call.block_view().numPoints.put_value(4000000),
            call.block_view().cs.put_value('CS1'),
            call.block_view().put_attribute_values(self.resolutions_and_use()),
            call.block_view().put_attribute_values(dict(
                timeArray=[207500, 207500, 207500, 207500, 207500],
                velocityMode=[0, 0, 0, 0, 2],
                userPrograms=[8, 8, 8, 8, 8],
                pointsToBuild=5,
                positionsA=pytest.approx([
                    0.4461796875, 0.285, 0.0775, -0.0836796875, -0.1375]),
                positionsB=[0.0, 0.0, 0.0, 0.0, 0.0])),
            call.block_view().buildProfile(),
            call.block_view().executeProfile_async(),
            call.wait_all(self.child.executeProfile_async.return_value),
            call.block_view().put_attribute_values(self.resolutions_and_use()),
            call.block_view().put_attribute_values(dict(
                timeArray=[
                    100000, 500000, 500000, 500000, 500000, 500000, 500000,
                    200000,
                    200000, 500000, 500000, 500000, 500000, 500000, 500000,
                    100000],
                velocityMode=[
                    2, 0, 0, 0, 0, 0, 1, 0,
                    2, 0, 0, 0, 0, 0, 1, 3],
                userPrograms=[
                    3, 4, 3, 4, 3, 4, 2, 8,
                    3, 4, 3, 4, 3, 4, 2, 8],
                pointsToBuild=16,
                positionsA=[
                    -0.125, 0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.6375,
                    0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375],
                positionsB=[
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05,
                    0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])),
            call.block_view().buildProfile()]

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_2_axis_move_to_start(self):
        self.do_configure(
            axes_to_scan=["x", "y"], x_pos=0.0, y_pos=0.2)
        assert self.context.mock_calls == [
            call.unsubscribe_all(),
            call.block_view('TST-PMAC'),
            call.block_view().numPoints.put_value(4000000),
            call.block_view().cs.put_value('CS1'),
            call.block_view().put_attribute_values(self.resolutions_and_use()),
            call.block_view().put_attribute_values(dict(
                timeArray=[282843, 282842],
                velocityMode=[0, 2],
                userPrograms=[8, 8],
                pointsToBuild=2,
                positionsA=[-0.068750000000000019, -0.13750000000000001],
                positionsB=[0.10000000000000001, 0.0])),
            call.block_view().buildProfile(),
            call.block_view().executeProfile_async(),
            call.wait_all(self.child.executeProfile_async.return_value),
            call.block_view().put_attribute_values(self.resolutions_and_use()),
            call.block_view().put_attribute_values(ANY),
            call.block_view().buildProfile()]

    @patch("malcolm.parts.pmac.pmactrajectorypart.POINTS_PER_BUILD", 4)
    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_update_step(self):
        self.do_configure(axes_to_scan=["x", "y"])
        positionsA = self.child.put_attribute_values.call_args_list[-1][0][0]["positionsA"]
        assert len(positionsA) == 11
        assert positionsA[-1] == 0.375
        assert self.o.end_index == 4
        assert len(self.o.completed_steps_lookup) == 11
        update_completed_steps = MagicMock()
        self.context.reset_mock()
        self.o.update_step(3, update_completed_steps, self.child)
        update_completed_steps.assert_called_once_with(1, self.o)
        assert not self.o.loading
        assert self.context.mock_calls == [
            call.block_view().put_attribute_values(self.resolutions_and_use()),
            call.block_view().put_attribute_values(dict(
                timeArray=[
                    500000, 500000, 500000, 500000, 100000],
                velocityMode=[
                    0, 0, 0, 1, 3],
                userPrograms=[
                    4, 3, 4, 2, 8],
                pointsToBuild=5,
                positionsA=[
                    0.25, 0.125, 0.0, -0.125, -0.1375],
                positionsB=[
                    0.1, 0.1, 0.1, 0.1, 0.1])),
            call.block_view().appendProfile()]

    def test_run(self):
        update = Mock()
        self.o.run(self.context, update)
        assert self.context.mock_calls == [
            call.block_view('TST-PMAC'),
            call.block_view().pointsScanned.subscribe_value(
                self.o.update_step, update, self.child),
            call.block_view().executeProfile()]

    def test_multi_run(self):
        self.do_configure(axes_to_scan=["x"])
        self.assertEqual(self.o.completed_steps_lookup,
                         [0, 0, 1, 1, 2, 2, 3, 3])
        self.context.reset_mock()
        self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.6375)
        assert self.context.mock_calls == [
            call.unsubscribe_all(),
            call.block_view('TST-PMAC'),
            call.block_view().numPoints.put_value(4000000),
            call.block_view().cs.put_value('CS1'),
            call.wait_all([]),
            call.block_view().put_attribute_values(
                self.resolutions_and_use(useB=False)),
            call.block_view().put_attribute_values(dict(
                timeArray=[
                    100000, 500000, 500000, 500000, 500000, 500000, 500000,
                    100000],
                velocityMode=[2, 0, 0, 0, 0, 0, 1, 3],
                userPrograms=[3, 4, 3, 4, 3, 4, 2, 8],
                pointsToBuild=8,
                positionsA=[
                    0.625, 0.5, 0.375, 0.25, 0.125, 0.0, -0.125, -0.1375])),
            call.block_view().buildProfile()]

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 0.2)
    def test_long_steps_lookup(self):
        self.do_configure(
            axes_to_scan=["x"], completed_steps=3, x_pos=0.62506, duration=14.0)
        assert self.child.mock_calls[-2] == call.put_attribute_values(dict(
            timeArray=[7143, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 3500000,
                       3500000, 7143],
            velocityMode=[2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 3],
            userPrograms=[3, 0, 4, 0, 3, 0, 4, 0, 3, 0, 4, 0, 2, 8],
            pointsToBuild=14,
            positionsA=[0.625,
                        0.5625,
                        0.5,
                        0.4375,
                        0.375,
                        0.3125,
                        0.25,
                        0.1875,
                        0.125,
                        0.0625,
                        0.0,
                        -0.0625,
                        -0.125,
                        -0.1250637755102041],
        ))
        self.assertEqual(self.o.completed_steps_lookup,
                         [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6])

    @patch("malcolm.parts.pmac.pmactrajectorypart.INTERPOLATE_INTERVAL", 2.0)
    def test_long_move(self):
        self.do_configure(axes_to_scan=["x"], x_pos=-10.1375)
        assert self.child.mock_calls[3] == call.put_attribute_values(dict(
            timeArray=[2080000, 2080000, 2080000, 2080000, 2080000],
            velocityMode=[0, 0, 0, 0, 2],
            userPrograms=[8, 8, 8, 8, 8],
            pointsToBuild=5,
            positionsA=[-8.2575,
                        -6.177499999999998,
                        -4.097499999999998,
                        -2.0174999999999983,
                        -0.1374999999999984],
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
