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
from malcolm.modules.BL18I.blocks import i18_fine_theta_manager_block,\
    i18_pmac_manager_block,\
    i18_table01_manager_block,\
    i18_table03_manager_block
from malcolm.modules.BL45P.blocks import hardware_scan_block,\
    pmac_manager_block,\
    sim_scan_block
from malcolm.modules.excalibur.blocks import excalibur_detector_driver_block,\
    excalibur_detector_manager_block,\
    fem_detector_driver_block,\
    fem_detector_manager_block
from malcolm.modules.profiling.blocks import profiling_block,\
    profiling_web_server_block



class TestBuiltin(unittest.TestCase):

    # ADAndor Blocks
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

    # ADPandABlocks blocks
    def test_pandablocks_manager_block(self):
        controller = call_with_params(
            pandablocks_runnable_block, Mock(), mriPrefix="mriPrefix",
            pvPrefix="PV:PRE", configDir="/tmp/malcolm")

        del controller

    # BL08I blocks
    def test_i08_det_scan_combined_block(self):
        controller = call_with_params(
            i08_det_scan_combined_block, Mock(), mri="mri", det="det",
            brick="brick", pandabox="pandabox", configDir="/tmp/malcolm")

        del controller

    def test_i08_pmac_manager_block(self):
        controller = call_with_params(
            i08_pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/tmp/malcolm")

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

    # BL18I blocks
    def test_i18_fine_theta_manager_block(self):
        controller = call_with_params(
            i18_fine_theta_manager_block, Mock(), mri="mri", det="det",
            brick="brick", pandabox="pandabox", configDir="/tmp/malcolm")

        del controller

    def test_i18_pmac_manager_block(self):
        controller = call_with_params(
            i18_pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/tmp/malcolm")

        del controller

    def test_i18_table01_manager_block(self):
        controller = call_with_params(
            i18_table01_manager_block, Mock(), mri="mri",
            det="det", brick="brick", pandabox="pandabox",
            configDir="/tmp/malcolm")

        del controller

    def test_i18_table03_manager_block(self):
        controller = call_with_params(
            i18_table03_manager_block, Mock(), mri="mri",
            det="det", brick="brick", pandabox="pandabox",
            configDir="/tmp/malcolm")

        del controller

    # BL45P blocks
    def test_hardware_scan_block(self):
        controller = call_with_params(
            hardware_scan_block, Mock(), mri="mri",
            mic="mic", pandabox="pandabox", zebra="zebra",
            brick="brick",
            configDir="/tmp/malcolm")

        del controller

    def test_pmac_manager_block(self):
        controller = call_with_params(
            pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/tmp/malcolm")

        del controller

    def test_sim_scan_block(self):
        controller = call_with_params(
            sim_scan_block, Mock(), mri="mri", sim="sim",
            configDir="/tmp/malcolm")

        del controller

    # Excalibur blocks
    def test_excalibur_detector_driver_block(self):
        controller = call_with_params(
            excalibur_detector_driver_block, Mock(), mri="mri", prefix="prefix")

        del controller

    def test_excalibur_detector_manager_block(self):
        controller = call_with_params(
            excalibur_detector_manager_block, Mock(), mriPrefix="mriPrefix",
            pvPrefix="pvPrefix",
            configDir="/tmp/malcolm")

        del controller

    def test_fem_detector_driver_block(self):
        controller = call_with_params(
            fem_detector_driver_block, Mock(), mri="mri",
            prefix="prefix")

        del controller

    def test_fem_detector_manager_block(self):
        controller = call_with_params(
            fem_detector_manager_block, Mock(), mriPrefix="mriPrefix",
            pvPrefix="pvPrefix",
            configDir="/tmp/malcolm")

        del controller

    # Profiling blocks
    def test_profiling_block(self):
        controller = call_with_params(
            profiling_block, Mock(), mri="mri",
            profilesDir="/tmp/malcolm")

        del controller

    def test_profiling_web_server_block(self):
        controller = call_with_params(
            profiling_web_server_block, Mock(),
            mri="mri",
            profilesDir="/tmp/malcolm")

        del controller