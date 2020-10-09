import pytest
from cothread import cothread
from mock import call

from malcolm.core import Process, TimeoutError
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.pmac.blocks import pmac_trajectory_block
from malcolm.modules.pmac.parts import PmacTrajectoryPart
from malcolm.testutil import ChildTestCase

SHOW_GRAPHS = False
# Uncomment this to show graphs when running under PyCharm
# SHOW_GRAPHS = "PYCHARM_HOSTED" in os.environ


class TestPMACTrajectoryPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.child = self.create_child_block(
            pmac_trajectory_block, self.process, mri="PMAC:TRAJ", pv_prefix="PV:PRE"
        )
        c = ManagerController("PMAC", "/tmp")
        self.o = PmacTrajectoryPart(name="pmac", mri="PMAC:TRAJ")
        c.add_part(self.o)
        self.process.add_controller(c)
        self.process.start()
        self.b = c.block_view()
        self.set_attributes(self.child, trajectoryProgVersion=2)

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_init(self):
        assert not self.b.pointsScanned.meta.writeable
        assert list(self.b.writeProfile.meta.takes.elements) == [
            "timeArray",
            "csPort",
            "velocityMode",
            "userPrograms",
            "a",
            "b",
            "c",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
        ]
        assert "executeProfile" in self.b
        assert "abortProfile" in self.b

    def test_write_profile_build(self):
        self.b.writeProfile(
            [1, 5, 2],
            "BRICK2CS1",
            velocityMode=[0, 1, 2],
            userPrograms=[0, 8, 0],
            x=[1, 2, 3],
            z=[4, 4.1, 4.2],
        )
        assert self.child.handled_requests.mock_calls == [
            call.put("numPoints", 4000000),
            call.put("cs", "BRICK2CS1"),
            call.put("useA", False),
            call.put("useB", False),
            call.put("useC", False),
            call.put("useU", False),
            call.put("useV", False),
            call.put("useW", False),
            call.put("useX", True),
            call.put("useY", False),
            call.put("useZ", True),
            call.put("pointsToBuild", 3),
            call.put("positionsX", [1, 2, 3]),
            call.put("positionsZ", [4, 4.1, 4.2]),
            call.put("timeArray", [1, 5, 2]),
            call.put("userPrograms", [0, 8, 0]),
            call.put("velocityMode", [0, 1, 2]),
            call.post("buildProfile"),
        ]

    def test_write_profile_append(self):
        self.b.writeProfile([1, 5, 2], x=[11, 12, 13], z=[14, 14.1, 14.2])
        assert self.child.handled_requests.mock_calls == [
            call.put("pointsToBuild", 3),
            call.put("positionsX", [11, 12, 13]),
            call.put("positionsZ", [14, 14.1, 14.2]),
            call.put("timeArray", [1, 5, 2]),
            call.put("userPrograms", pytest.approx([0, 0, 0])),
            call.put("velocityMode", pytest.approx([0, 0, 0])),
            call.post("appendProfile"),
        ]

    def test_execute_profile(self):
        self.mock_when_value_matches(self.child)
        self.b.executeProfile()
        assert self.child.handled_requests.mock_calls == [
            call.post("executeProfile"),
            call.when_value_matches("pointsScanned", 0, None),
        ]

    def test_execute_profile_not_enough(self):
        def _handle_post(request):
            cothread.Sleep(1)
            return [request.return_response(1)]

        self.child._handle_post = _handle_post
        self.o.total_points = 2
        future = self.b.executeProfile_async()
        self.set_attributes(self.child, pointsScanned=1)
        with self.assertRaises(TimeoutError) as cm:
            future.result(timeout=2)
        assert str(cm.exception) == (
            "Timeout waiting for [When(PMAC:TRAJ.pointsScanned.value, equals_2, "
            "last=1)]"
        )
