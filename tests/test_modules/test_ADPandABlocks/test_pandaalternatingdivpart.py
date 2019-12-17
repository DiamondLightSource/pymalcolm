from malcolm.testutil import ChildTestCase
from malcolm.modules.ADPandABlocks.parts import PandAAlternatingDivPart
from malcolm.modules.ADPandABlocks.blocks import panda_alternating_div_block
from malcolm.core import Context, Process
from malcolm.modules.builtin.controllers import ManagerController

class TestPandAAlternatingDivPart(ChildTestCase):
    def setUp(self):

        self.process = Process()
        self.context = Context(self.process)

        self.panda = ManagerController("PANDA", "/tmp")
        #self.process.add_controller(self.panda)

        self.child = self.create_child_block(panda_alternating_div_block,
                                             self.process,
                                             mri="PANDA",
                                             panda="panda")

        self.part_under_test = \
            PandAAlternatingDivPart("alternatingDivPart",
                                    "PANDA")

    def tearDown(self):
        pass

    def test_validate(self):
        detector_table = None
        self.part_under_test.on_validate(context=self.context,
                                         detectors=detector_table)