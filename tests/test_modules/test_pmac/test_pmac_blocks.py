import os
import sys
import unittest
from mock import Mock
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from malcolm.core import call_with_params
from malcolm.modules.pmac.blocks import pmac_trajectory_block, \
    compound_motor_block, raw_motor_block


class TestBuiltin(unittest.TestCase):
    def test_compound_motor_block(self):
        controller = call_with_params(
            compound_motor_block, Mock(), mri="my_mri", prefix="PV:PRE",
            scannable="scan")
        assert controller.parts["doneMoving"].params.rbv == "PV:PRE.DMOV"
        assert list(controller.block_view()) == [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'position',
            'doneMoving',
            'accelerationTime',
            'maxVelocity',
            'resolution',
            'offset',
            'outLink',
            'scannable',
            'velocitySettle']

    def test_raw_motor_block(self):
        controller = call_with_params(
            raw_motor_block, Mock(), mri="my_mri", prefix="PV:PRE",
            motorPrefix="MOT:PRE", scannable="scan")
        assert controller.parts["doneMoving"].params.rbv == "MOT:PRE.DMOV"
        assert controller.parts["csAxis"].params.pv == "PV:PRE:CsAxis"
        assert list(controller.block_view()) == [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'position',
            'doneMoving',
            'accelerationTime',
            'maxVelocity',
            'resolution',
            'offset',
            'csPort',
            'csAxis',
            'scannable',
            'velocitySettle']

    def test_pmac_trajectory_block(self):
        controller = call_with_params(
            pmac_trajectory_block, Mock(), mri="my_mri", prefix="PV:PRE",
            statPrefix="PV:STAT")
        assert controller.parts["i10"].params.rbv == "PV:STAT:I10"
        assert controller.parts["buildProfile"].params.pv == \
               "PV:PRE:ProfileBuild"
        assert list(controller.block_view()) == [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'i10',
            'cs',
            'buildProfile',
            'buildMessage',
            'executeProfile',
            'executeMessage',
            'appendProfile',
            'appendMessage',
            'scanPercentage',
            'pointsScanned',
            'abortProfile',
            'timeArray',
            'velocityMode',
            'userPrograms',
            'numPoints',
            'pointsToBuild',
            'useA',
            'positionsA',
            'resolutionA',
            'offsetA',
            'useB',
            'positionsB',
            'resolutionB',
            'offsetB',
            'useC',
            'positionsC',
            'resolutionC',
            'offsetC',
            'useU',
            'positionsU',
            'resolutionU',
            'offsetU',
            'useV',
            'positionsV',
            'resolutionV',
            'offsetV',
            'useW',
            'positionsW',
            'resolutionW',
            'offsetW',
            'useX',
            'positionsX',
            'resolutionX',
            'offsetX',
            'useY',
            'positionsY',
            'resolutionY',
            'offsetY',
            'useZ',
            'positionsZ',
            'resolutionZ',
            'offsetZ']

