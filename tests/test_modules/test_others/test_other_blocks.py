import os
import sys
import unittest
from mock import Mock
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from malcolm.core import call_with_params
from malcolm.modules.ADAndor.blocks import andor_detector_driver_block,\
andor_detector_manager_block

class TestBuiltin(unittest.TestCase):
    def test_andor_detector_driver_block(self):
        controller = call_with_params(
            andor_detector_driver_block, Mock(), mri="my_mri", prefix="PV:PRE")

        del controller

    def test_andor_detector_manager_block(self):
        controller = call_with_params(
            andor_detector_manager_block, Mock(), mriPrefix="my_mri", pvPrefix="PV:PRE",
            configDir="/dls/tmp")

        del controller