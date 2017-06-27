from mock import Mock

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
    excalibur_detector_runnable_block,\
    fem_detector_driver_block,\
    fem_detector_runnable_block
from malcolm.modules.profiling.blocks import profiling_web_server_block
from malcolm.testutil import ChildTestCase


class TestBuiltin(ChildTestCase):
    # BL08I blocks
    def test_i08_det_scan_combined_block(self):
        self.create_child_block(
            i08_det_scan_combined_block, Mock(), mri="mri", det="det",
            brick="brick", pandabox="pandabox", configDir="/tmp")

    def test_i08_pmac_manager_block(self):
        self.create_child_block(
            i08_pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/tmp")

    def test_i08_scan_butterfly_block(self):
        self.create_child_block(
            i08_scan_butterfly_block, Mock(), mri="mri",
            configDir="/tmp", brick="brick", pandabox="pandabox")

    def test_i08_scan_combined_block(self):
        self.create_child_block(
            i08_scan_combined_block, Mock(), mri="mri",
            brick="brick", pandabox="pandabox", configDir="/tmp")

    def test_i08_two_det_scan_combined_block(self):
        self.create_child_block(
            i08_two_det_scan_combined_block, Mock(), mri="mri", det1="det1",
            det2="det2",
            brick="brick", pandabox="pandabox", configDir="/tmp")

    # BL18I blocks
    def test_i18_fine_theta_manager_block(self):
        self.create_child_block(
            i18_fine_theta_manager_block, Mock(), mri="mri", det="det",
            brick="brick", pandabox="pandabox", configDir="/tmp")

    def test_i18_pmac_manager_block(self):
        self.create_child_block(
            i18_pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/tmp")

    def test_i18_table01_manager_block(self):
        self.create_child_block(
            i18_table01_manager_block, Mock(), mri="mri",
            det="det", brick="brick", pandabox="pandabox",
            configDir="/tmp")

    def test_i18_table03_manager_block(self):
        self.create_child_block(
            i18_table03_manager_block, Mock(), mri="mri",
            det="det", brick="brick", pandabox="pandabox",
            configDir="/tmp")

    # BL45P blocks
    def test_hardware_scan_block(self):
        self.create_child_block(
            hardware_scan_block, Mock(), mri="mri",
            mic="mic", pandabox="pandabox", zebra="zebra",
            brick="brick",
            configDir="/tmp")

    def test_pmac_manager_block(self):
        self.create_child_block(
            pmac_manager_block, Mock(), mriPrefix="mriPrefix",
            configDir="/tmp")

    def test_sim_scan_block(self):
        self.create_child_block(
            sim_scan_block, Mock(), mri="mri", sim="sim",
            configDir="/tmp")

    # Excalibur blocks
    def test_excalibur_detector_driver_block(self):
        self.create_child_block(
            excalibur_detector_driver_block, Mock(), mri="mri", prefix="prefix")

    def test_excalibur_detector_runnable_block(self):
        self.create_child_block(
            excalibur_detector_runnable_block, Mock(), mriPrefix="mriPrefix",
            pvPrefix="pvPrefix",
            configDir="/tmp")

    def test_fem_detector_driver_block(self):
        self.create_child_block(
            fem_detector_driver_block, Mock(), mri="mri",
            prefix="prefix")

    def test_fem_detector_runnable_block(self):
        self.create_child_block(
            fem_detector_runnable_block, Mock(), mriPrefix="mriPrefix",
            pvPrefix="pvPrefix",
            configDir="/tmp")

    def test_profiling_web_server_block(self):
        self.create_child_block(
            profiling_web_server_block, Mock(),
            mri="mri")
