import os

import numpy as np
import pytest
from cothread import cothread
from mock import Mock, call, patch
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process
from malcolm.modules.pmac.blocks import pmac_trajectory_block
from malcolm.modules.pmac.infos import MotorInfo
from malcolm.modules.pmac.parts import PmacTrajectoryPart
from malcolm.testutil import ChildTestCase

SHOW_GRAPHS = False
# Uncomment this to show graphs when running under PyCharm
# SHOW_GRAPHS = "PYCHARM_HOSTED" in os.environ


class TestPMACTrajectoryPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            pmac_trajectory_block, self.process, mri="PMAC:TRAJ",
            prefix="PV:PRE")
        self.o = PmacTrajectoryPart(name="pmac", mri="PMAC:TRAJ")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        self.o.init(self.context)

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_init(self):
        registrar = Mock()
        self.o.setup(registrar)
        assert registrar.add_attribute_model.call_args_list == [
            call("outputTriggers", self.o.output_triggers,
                 self.o.output_triggers.set_value),
            call("pointsScanned", self.o.points_scanned)
        ]
        assert registrar.add_method_model.call_args_list == [
            call(self.o.write_profile, "writeProfile"),
            call(self.o.execute_profile, "executeProfile"),
            call(self.o.abort_profile, "abortProfile")
        ]

    def test_write_profile_build(self):
        self.o.write_profile(
            [1, 1.1, 0.9], "BRICK2CS1", velocityMode=[0, 1, 2],
            userPrograms=[0, 8, 0], x=[1, 2, 3], z=[4, 4.1, 4.2]
        )
        assert self.child.handled_requests.mock_calls == [
            call.put('numPoints', 4000000),
            call.put('cs', 'BRICK2CS1'),
            call.put('useA', False),
            call.put('useB', False),
            call.put('useC', False),
            call.put('useU', False),
            call.put('useV', False),
            call.put('useW', False),
            call.put('useX', True),
            call.put('useY', False),
            call.put('useZ', True),
            call.put('pointsToBuild', 3),
            call.put('positionsX', [1, 2, 3]),
            call.put('positionsZ', [4, 4.1, 4.2]),
            call.put('timeArray', [1, 1.1, 0.9]),
            call.put('userPrograms', [0, 8, 0]),
            call.put('velocityMode', [0, 1, 2]),
            call.post('buildProfile')
        ]

    def test_write_profile_append(self):
        self.o.write_profile(
            [1, 1.1, 0.9], x=[11, 12, 13], z=[14, 14.1, 14.2]
        )
        assert self.child.handled_requests.mock_calls == [
            call.put('pointsToBuild', 3),
            call.put('positionsX', [11, 12, 13]),
            call.put('positionsZ', [14, 14.1, 14.2]),
            call.put('timeArray', [1, 1.1, 0.9]),
            call.put('userPrograms', pytest.approx([0, 0, 0])),
            call.put('velocityMode', pytest.approx([0, 0, 0])),
            call.post('appendProfile')
        ]

    def test_execute_profile(self):
        self.o.execute_profile()
        assert self.child.handled_requests.mock_calls == [
            call.post('executeProfile'),
            call.when_values_matches('pointsScanned', 0, None, 0.1, None)
        ]

    def test_execute_profile_not_enough(self):
        def _handle_post(request):
            cothread.Sleep(2)
            return [request.return_response(1)]
        self.child._handle_post = _handle_post
        self.o.total_points = 2
        sp = cothread.Spawn(self.o.execute_profile)
        self.set_attributes(self.child, pointsScanned=1)
        with self.assertRaises(AssertionError) as cm:
            sp.Wait(3)

