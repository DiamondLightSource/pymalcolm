from mock import call, Mock

from malcolm.core import Context, Process, PartRegistrar
from malcolm.modules.pmac.parts import CSPart
from malcolm.modules.pmac.blocks import cs_block
from malcolm.testutil import ChildTestCase


class TestCSPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            cs_block, self.process, mri="PMAC:CS1",
            prefix="PV:PRE")
        self.set_attributes(self.child, port="PMAC2CS1")
        self.o = CSPart(mri="PMAC:CS1", cs=1)
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        self.o.init(self.context)

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_setup(self):
        registrar = Mock(spec=PartRegistrar)
        self.o.setup(registrar)
        registrar.add_method_model.assert_called_once_with(
            self.o.move, "moveCS1")

    def test_move(self):
        self.mock_when_value_matches(self.child)
        self.o.move(a=32, c=19.1, move_time=2.3)
        assert self.child.handled_requests.mock_calls == [
            call.put('deferMoves', True),
            call.put('csMoveTime', 2.3),
            call.put('demandA', 32),
            call.put('demandC', 19.1),
            call.when_value_matches('demandA', 32, None),
            call.when_value_matches('demandC', 19.1, None),
            call.put('deferMoves', False)
        ]
