import os
import sys
import unittest
from mock import Mock
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from malcolm.core import call_with_params
from malcolm.modules.ADAndor.blocks import andor_detector_driver_block,\
andor_detector_manager_block
from malcolm.modules.ADPandABlocks.blocks import pandablocks_runnable_block
from malcolm.modules.BL08I.blocks import i08_det_scan_combined_block,\
    i08_pmac_manager_block,\
    i08_scan_butterfly_block,\
    i08_scan_combined_block,\
    i08_two_det_scan_combined_block

class TestBuiltin(unittest.TestCase):
    def test_andor_detector_driver_block(self):
        controller = call_with_params(
            andor_detector_driver_block, Mock(), mri="my_mri", prefix="PV:PRE")

        del controller

    def test_andor_detector_manager_block(self):
        controller = call_with_params(
            andor_detector_manager_block, Mock(), mriPrefix="my_mri",
            pvPrefix="PV:PRE",
            configDir="/tmp/malcolm")

        del controller

    def test_pandablocks_manager_block(self):
        controller = call_with_params(
            pandablocks_runnable_block, Mock(), mriPrefix="mriPrefix",
            pvPrefix="PV:PRE", configDir="/tmp/malcolm")

        del controller

    def test_i08_det_scan_combined_block(self):
        controller = call_with_params(
            i08_det_scan_combined_block, Mock(), mri="mri", det="det",
            brick="brick", pandabox="pandabox", configDir="/tmp/malcolm")

        del controller

    def test_i08_pmac_manager_block(self):
        controller = call_with_params(
            i08_pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/dls/tmp")

        del controller

    def test_i08_scan_butterfly_block(self):
        controller = call_with_params(
            i08_scan_butterfly_block, Mock(), mri="mri",
            configDir="/tmp/malcolm", brick="brick", pandabox="pandabox")

        del controller

    def test_i08_scan_combined_block(self):
        controller = call_with_params(
            i08_scan_combined_block, Mock(), mri="mri",
            brick="brick", pandabox="pandabox", configDir="/tmp/malcolm")

        del controller

    def test_i08_two_det_scan_combined_block(self):
        controller = call_with_params(
            i08_two_det_scan_combined_block, Mock(), mri="mri", det1="det1",
            det2="det2",
            brick="brick", pandabox="pandabox", configDir="/tmp/malcolm")

        del controller
