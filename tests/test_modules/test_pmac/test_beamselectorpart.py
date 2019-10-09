import unittest, os, tempfile, shutil

from typing import Union

from malcolm.core import Part, Controller, Process, Context, PartRegistrar
from malcolm.modules.builtin.controllers import BasicController, ManagerController
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.pmac.parts import BeamSelectorPart

from mock import Mock, call, patch, ANY
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator

class TestBeamSelectorPart(ChildTestCase):

    def setUp(self):
        self.process = Process("test_process")
        self.context = Context(self.process)

        bs_block = make_block_creator(
            __file__, "test_bs_manager_block.yaml")

        self.child = self.create_child_block(bs_block,
                                             self.process,
                                             mri_prefix="BL45P-ML-MMP-01",
                                             config_dir="/tmp")
        # These are the child blocks we are interested in
        self.child_bs = self.process.get_controller("BL45P-ML-CHOP-01:VER")
        self.child_y = self.process.get_controller("BL45P-ML-STAGE-01:Y")
        self.child_cs1 = self.process.get_controller("BL45P-ML-MMP-01:CS1")
        self.child_traj = self.process.get_controller("BL45P-ML-MMP-01:TRAJ")
        self.child_status = self.process.get_controller("BL45P-ML-MMP-01:STATUS")
        # CS1 needs to have the right port otherwise we will error
        self.set_attributes(self.child_cs1, port="CS1")

        self.part = BeamSelectorPart(name="motorMovePart", mri="BL45P-ML-CHOP-01:VER") # will be renamed to MotorMovePart

        self.context.set_notify_dispatch_request(self.part.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_init(self):

        self.part.move(self.context, 20.0)

        assert self.part.x == 20.0, "BS axis hasn't moved."

        pass