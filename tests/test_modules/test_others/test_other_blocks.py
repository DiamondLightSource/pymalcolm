from mock import Mock

from malcolm.modules.excalibur.blocks import excalibur_driver_block,\
    excalibur_detector_runnable_block,\
    fem_driver_block,\
    fem_detector_runnable_block
from malcolm.modules.profiling.blocks import profiling_web_server_block
from malcolm.testutil import ChildTestCase


class TestBuiltin(ChildTestCase):
    # Excalibur blocks
    def test_excalibur_driver_block(self):
        self.create_child_block(
            excalibur_driver_block, Mock(), mri="mri", prefix="prefix")

    def test_excalibur_detector_runnable_block(self):
        self.create_child_block(
            excalibur_detector_runnable_block, Mock(), mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp")

    def test_fem_driver_block(self):
        self.create_child_block(
            fem_driver_block, Mock(), mri="mri",
            prefix="prefix")

    def test_fem_detector_runnable_block(self):
        self.create_child_block(
            fem_detector_runnable_block, Mock(), mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp")

    def test_profiling_web_server_block(self):
        self.create_child_block(
            profiling_web_server_block, Mock(),
            mri="mri")
