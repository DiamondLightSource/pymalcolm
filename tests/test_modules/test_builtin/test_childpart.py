import unittest

from malcolm.core import Part, Process, Table, Context, StringMeta, \
    PartRegistrar, Port
from malcolm.modules.builtin.controllers import BasicController, \
    ManagerController
from malcolm.modules.builtin.infos import InPortInfo, OutPortInfo
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import LayoutTable

sm = ManagerController.state_set


class PortsPart(Part):

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PortsPart, self).setup(registrar)
        # note 3rd part of inport tag is its disconnected value
        in_tag = "inport:int32:"
        in_name = "inportConnector"
        in_port = StringMeta(in_name,
                             [in_tag, "config:1"]).create_attribute_model()
        registrar.add_attribute_model(in_name, in_port, in_port.set_value)

        out_name = "outportConnector"
        out_tag = "outport:int32:%s" % self.name
        out_port = StringMeta(in_name, [out_tag]).create_attribute_model()
        registrar.add_attribute_model(out_name, out_port, out_port.set_value)


class TestChildPart(unittest.TestCase):

    def checkState(self, state):
        assert self.c.state.value == state

    def makeChildBlock(self, blockMri):
        controller = BasicController(blockMri)
        controller.add_part(PortsPart(name='Connector%s' % blockMri[-1]))
        part = ChildPart(
            mri=blockMri, name='part%s' % blockMri, initial_visibility=True)
        self.p.add_controller(controller)
        return part, controller

    def setUp(self):
        self.p = Process('process1')

        self.p1, self.c1 = self.makeChildBlock('child1')
        self.p2, self.c2 = self.makeChildBlock('child2')
        self.p3, self.c3 = self.makeChildBlock('child3')
        self.c1._block.inportConnector.set_value('Connector3')
        self.c2._block.inportConnector.set_value('Connector1')
        self.c3._block.inportConnector.set_value('Connector2')

        # create a root block for the child blocks to reside in
        self.c = ManagerController(mri='mainBlock', config_dir="/tmp")
        for part in [self.p1, self.p2, self.p3]:
            self.c.add_part(part)
        self.p.add_controller(self.c)

        # Start the process
        # check that do_initial_reset works asynchronously
        assert self.c.state.value == sm.DISABLED
        self.p.start()
        assert self.c.state.value == sm.READY

    def tearDown(self):
        self.p.stop(timeout=1)

    def test_init(self):
        for controller in (self.c1, self.c2, self.c3):
            b = self.p.block_view(controller.mri)
            assert b.outportConnector.value == ''
        assert self.c.exports.meta.elements["source"].choices == [
            'partchild1.health',
            'partchild1.inportConnector',
            'partchild1.outportConnector',
            'partchild2.health',
            'partchild2.inportConnector',
            'partchild2.outportConnector',
            'partchild3.health',
            'partchild3.inportConnector',
            'partchild3.outportConnector'
        ]
        assert len(self.c.port_info) == 3
        port_info = self.c.port_info["partchild1"]
        assert len(port_info) == 2
        info_in = port_info[0]
        assert isinstance(info_in, InPortInfo)
        assert info_in.name == "inportConnector"
        assert info_in.port == Port.INT32
        assert info_in.value == "Connector3"
        assert info_in.disconnected_value == ""
        info_out = port_info[1]
        assert isinstance(info_out, OutPortInfo)
        assert info_out.name == "outportConnector"
        assert info_out.port == Port.INT32
        assert info_out.connected_value == "Connector1"

    def test_layout(self):
        b = self.p.block_view("mainBlock")

        new_layout = LayoutTable(
            name=["partchild1", "partchild2", "partchild3"],
            mri=["part1", "part2", "part3"],
            x=[10, 11, 12],
            y=[20, 21, 22],
            visible=[True, True, True])
        b.layout.put_value(new_layout)
        assert self.c.parts['partchild1'].x == 10
        assert self.c.parts['partchild1'].y == 20
        assert self.c.parts['partchild1'].visible == True
        assert self.c.parts['partchild2'].x == 11
        assert self.c.parts['partchild2'].y == 21
        assert self.c.parts['partchild2'].visible == True
        assert self.c.parts['partchild3'].x == 12
        assert self.c.parts['partchild3'].y == 22
        assert self.c.parts['partchild3'].visible == True

        new_layout.visible = [True, False, True]
        b.layout.put_value(new_layout)
        assert self.c.parts['partchild1'].visible == True
        assert self.c.parts['partchild2'].visible == False
        assert self.c.parts['partchild3'].visible == True

    def test_sever_all_inports(self):
        b = self.p.block_view("mainBlock")
        b1, b2, b3 = (self.c1.make_view(), self.c2.make_view(),
                      self.c3.make_view())
        new_layout = dict(
            name=["partchild1"], mri=[""], x=[0], y=[0], visible=[False])
        b.layout.put_value(new_layout)
        assert b1.inportConnector.value == ''
        assert b2.inportConnector.value == ''
        assert b3.inportConnector.value == 'Connector2'

    def test_load_save(self):
        b1 = self.c1.make_view()
        context = Context(self.p)
        structure1 = self.p1.save(context)
        expected = dict(inportConnector="Connector3")
        assert structure1 == expected
        b1.inportConnector.put_value("blah")
        structure2 = self.p1.save(context)
        expected = dict(inportConnector="blah")
        assert structure2 == expected
        self.p1.load(context, dict(inportConnector="blah_again"))
        assert b1.inportConnector.value == "blah_again"
