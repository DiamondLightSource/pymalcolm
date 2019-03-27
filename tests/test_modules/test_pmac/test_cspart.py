from mock import call, Mock

from malcolm.core import Context, Process, PartRegistrar
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.pmac.parts import CSPart
from malcolm.modules.pmac.blocks import cs_block
from malcolm.testutil import ChildTestCase


class TestCSPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.child = self.create_child_block(
            cs_block, self.process, mri="PMAC:CS1",
            prefix="PV:PRE")
        self.set_attributes(self.child, port="PMAC2CS1")
        c = ManagerController("PMAC", "/tmp")
        c.add_part(CSPart(mri="PMAC:CS1", cs=1))
        self.process.add_controller(c)
        self.process.start()
        self.b = c.block_view()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_init(self):
        assert "moveCS1" in self.b

    def test_move(self):
        self.mock_when_value_matches(self.child)
        self.b.moveCS1(a=32, c=19.1, moveTime=2.3)
        assert self.child.handled_requests.mock_calls == [
            call.put('deferMoves', True),
            call.put('csMoveTime', 2.3),
            call.put('demandA', 32),
            call.put('demandC', 19.1),
            call.when_value_matches('demandA', 32, None),
            call.when_value_matches('demandC', 19.1, None),
            call.put('deferMoves', False)
        ]
