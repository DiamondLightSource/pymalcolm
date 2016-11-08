import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.core.syncfactory import SyncFactory
from malcolm.core import Process
from malcolm.controllers.managercontroller import ManagerController

class TestChildPart(unittest.TestCase):

    def setUp(self):
        params = dict(
            name="MyLayout",
            mri="aChildName")
        params = ChildPart.MethodMeta.prepare_input_map(**params)

        #self.s = SyncFactory('threading')
        #self.process = Process('process', self.s)
        self.process = Mock()
        self.child = ChildPart(self.process, params)

        # add part to a block so we can easily test hook
        parts = [self.child]
        params = dict(
            mri="block")
        params = ManagerController.MethodMeta.prepare_input_map(**params)
        self.controller = ManagerController(self.process, parts, params)
        self.block = self.controller.block

    def test_init(self):
        self.assertEqual(self.child.name, 'MyLayout')
        self.assertEqual(self.child.params.mri, 'aChildName')
        self.process.get_block.assert_called_with('aChildName')


if __name__ == "__main__":
    unittest.main(verbosity=2)
