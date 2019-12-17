from malcolm.testutil import ChildTestCase
from malcolm.modules.ADPandABlocks.parts import PandAAlternatingDivPart
from malcolm.modules.ADPandABlocks.blocks import panda_alternating_div_block
from malcolm.core import Context, Process
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.scanning.util import DetectorTable

class TestPandAAlternatingDivPart(ChildTestCase):
    def setUp(self):

        self.process = Process()
        self.context = Context(self.process)

        self.panda = ManagerController("ML-PANDA-01", "/tmp")
        #self.process.add_controller(self.panda)

        self.child = self.create_child_block(panda_alternating_div_block,
                                             self.process,
                                             mri="ML-PANDA-01",
                                             panda="ML-PANDA-01")

        self.part_under_test = \
            PandAAlternatingDivPart(name="alternatingDivPart",
                                    mri="ML-PANDA-01")

    def tearDown(self):
        pass

    def test_validate(self):
        detector_table = DetectorTable([True],
                                       ["PandA"],
                                       ["ML-PANDA-01"],
                                       [1.0],
                                       [2])
        self.part_under_test.on_validate(context=self.context,
                                         detectors=detector_table)