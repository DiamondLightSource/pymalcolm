from mock import call
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Context, Process
from malcolm.modules.pmac.blocks import raw_motor_block
from malcolm.modules.pmac.parts import MotorPreMovePart
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.testutil import ChildTestCase


class TestMotorPreMovePart(ChildTestCase):
    def setUp(self):
        self.process = Process("test_process")
        self.context = Context(self.process)

        # Create a raw motor mock to handle axis request
        self.child = self.create_child_block(
            raw_motor_block, self.process, mri="BS", pv_prefix="PV:PRE"
        )
        # Add Beam Selector object
        self.o = MotorPreMovePart(name="MotorPreMovePart", mri="BS", demand=50)

        controller = RunnableController("SCAN", "/tmp")
        controller.add_part(self.o)

        self.process.add_controller(controller)
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_bs(self):
        b = self.context.block_view("SCAN")
        generator = CompoundGenerator([LineGenerator("x", "mm", 0, 1, 10)], [], [], 0.1)
        b.configure(generator)

        self.o.on_configure(self.context)

        assert self.child.handled_requests.mock_calls == [call.put("demand", 50)]
