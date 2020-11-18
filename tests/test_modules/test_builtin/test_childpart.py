import unittest

from malcolm.core import (
    Context,
    Part,
    PartRegistrar,
    Port,
    Process,
    StringMeta,
    config_tag,
)
from malcolm.modules.builtin.controllers import BasicController, ManagerController
from malcolm.modules.builtin.infos import SinkPortInfo, SourcePortInfo
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import AVisibleArray, LayoutTable

sm = ManagerController.state_set


class PortsPart(Part):
    def setup(self, registrar: PartRegistrar) -> None:
        super(PortsPart, self).setup(registrar)
        attr = StringMeta(
            tags=[Port.INT32.sink_port_tag(""), config_tag(1)]
        ).create_attribute_model()
        registrar.add_attribute_model("sinkportConnector", attr, attr.set_value)

        attr = StringMeta(
            tags=[Port.INT32.source_port_tag(self.name)]
        ).create_attribute_model()
        registrar.add_attribute_model("sourceportConnector", attr, attr.set_value)


class TestChildPart(unittest.TestCase):
    def checkState(self, state):
        assert self.c.state.value == state

    def makeChildBlock(self, block_mri):
        controller = BasicController(block_mri)
        controller.add_part(PortsPart(name="Connector%s" % block_mri[-1]))
        part = ChildPart(
            mri=block_mri,
            name="part%s" % block_mri,
            stateful=False,
            initial_visibility=True,
        )
        self.p.add_controller(controller)
        return part, controller

    def setUp(self):
        self.p = Process("process1")

        self.p1, self.c1 = self.makeChildBlock("child1")
        self.p2, self.c2 = self.makeChildBlock("child2")
        self.p3, self.c3 = self.makeChildBlock("child3")
        self.c1._block.sinkportConnector.set_value("Connector3")
        self.c2._block.sinkportConnector.set_value("Connector1")
        self.c3._block.sinkportConnector.set_value("Connector2")

        # create a root block for the child blocks to reside in
        self.c = ManagerController(mri="mainBlock", config_dir="/tmp")
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
            assert b.sourceportConnector.value == ""
        assert self.c.exports.meta.elements["source"].choices == [
            "partchild1.health",
            "partchild1.sinkportConnector",
            "partchild1.sourceportConnector",
            "partchild2.health",
            "partchild2.sinkportConnector",
            "partchild2.sourceportConnector",
            "partchild3.health",
            "partchild3.sinkportConnector",
            "partchild3.sourceportConnector",
        ]
        assert len(self.c.port_info) == 3
        port_info = self.c.port_info["partchild1"]
        assert len(port_info) == 2
        info_in = port_info[0]
        assert isinstance(info_in, SinkPortInfo)
        assert info_in.name == "sinkportConnector"
        assert info_in.port == Port.INT32
        assert info_in.value == "Connector3"
        assert info_in.disconnected_value == ""
        info_out = port_info[1]
        assert isinstance(info_out, SourcePortInfo)
        assert info_out.name == "sourceportConnector"
        assert info_out.port == Port.INT32
        assert info_out.connected_value == "Connector1"

    def test_layout(self):
        b = self.p.block_view("mainBlock")

        new_layout = LayoutTable(
            name=["partchild1", "partchild2", "partchild3"],
            mri=["part1", "part2", "part3"],
            x=[10, 11, 12],
            y=[20, 21, 22],
            visible=[True, True, True],
        )
        b.layout.put_value(new_layout)
        assert self.c.parts["partchild1"].x == 10
        assert self.c.parts["partchild1"].y == 20
        assert self.c.parts["partchild1"].visible == AVisibleArray(True)
        assert self.c.parts["partchild2"].x == 11
        assert self.c.parts["partchild2"].y == 21
        assert self.c.parts["partchild2"].visible == AVisibleArray(True)
        assert self.c.parts["partchild3"].x == 12
        assert self.c.parts["partchild3"].y == 22
        assert self.c.parts["partchild3"].visible == AVisibleArray(True)

        new_layout.visible = [True, False, True]
        b.layout.put_value(new_layout)
        assert self.c.parts["partchild1"].visible == AVisibleArray(True)
        assert self.c.parts["partchild2"].visible == AVisibleArray(False)
        assert self.c.parts["partchild3"].visible == AVisibleArray(True)

    def test_sever_all_sink_ports(self):
        b = self.p.block_view("mainBlock")
        b1, b2, b3 = (self.c1.block_view(), self.c2.block_view(), self.c3.block_view())
        new_layout = dict(name=["partchild1"], mri=[""], x=[0], y=[0], visible=[False])
        b.layout.put_value(new_layout)
        assert b1.sinkportConnector.value == ""
        assert b2.sinkportConnector.value == ""
        assert b3.sinkportConnector.value == "Connector2"

    def test_load_save(self):
        b1 = self.c1.block_view()
        context = Context(self.p)
        structure1 = self.p1.on_save(context)
        expected = dict(sinkportConnector="Connector3")
        assert structure1 == expected
        b1.sinkportConnector.put_value("blah")
        structure2 = self.p1.on_save(context)
        expected = dict(sinkportConnector="blah")
        assert structure2 == expected
        self.p1.on_load(context, dict(sinkportConnector="blah_again"))
        assert b1.sinkportConnector.value == "blah_again"
