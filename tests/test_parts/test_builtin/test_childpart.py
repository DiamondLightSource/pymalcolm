import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from mock import Mock, ANY

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.controllers.builtin import BaseController, ManagerController
from malcolm.core import Part, Process, Table, call_with_params, Context
from malcolm.parts.builtin import ChildPart
from malcolm.vmetas.builtin.stringmeta import StringMeta

sm = ManagerController.stateSet


class PortsPart(Part):
    in_port = ''
    out_port = ''

    def write_in_port(self, val):
        self.in_port = val

    def write_out_port(self, val):
        self.out_port = val

    def create_attributes(self):
        for data in super(PortsPart, self).create_attributes():
            yield data
        # note 3rd part of inport tag is its disconnected value
        in_tag = "inport:int32:"
        in_name = "inport%s" % self.name
        in_port = StringMeta(in_name, [in_tag, "config"]).create_attribute()
        in_port.meta.set_writeable_in(sm.READY)
        yield in_name, in_port, in_port.set_value

        out_name = "outport%s" % self.name
        out_tag = "outport:int32:%s" %self.name
        out_port = StringMeta(in_name, [out_tag]).create_attribute()
        out_port.meta.set_writeable_in(sm.READY)
        yield out_name, out_port, out_port.set_value


class TestChildPart(unittest.TestCase):

    def checkState(self, state):
        self.assertEqual(self.c.state.value, state)

    def makeChildBlock(self, blockMri):
        controller = call_with_params(
            BaseController, self.p, [PortsPart(name='Connector')], mri=blockMri)
        part = call_with_params(
            ChildPart, mri=blockMri, name='part%s' % blockMri)
        self.p.add_controller(blockMri, controller)
        return part, controller

    def setUp(self):
        self.p = Process('process1')

        self.p1, self.c1 = self.makeChildBlock('child1')
        self.p2, self.c2 = self.makeChildBlock('child2')
        self.p3, self.c3 = self.makeChildBlock('child3')

        # create a root block for the child blocks to reside in
        parts = [self.p1, self.p2, self.p3]
        self.c = call_with_params(
            ManagerController, self.p, parts, mri='mainBlock', configDir="/tmp")
        self.p.add_controller('mainBlock', self.c)

        # Start the process
        # check that do_initial_reset works asynchronously
        assert self.c.state.value == sm.DISABLED
        self.p.start()
        assert self.c.state.value == sm.READY

    def tearDown(self):
        self.p.stop()

    def test_init(self):
        for controller in (self.c1, self.c2, self.c3):
            b = self.p.block_view(controller.mri)
            assert b.inportConnector.value == ''
            assert b.outportConnector.value == ''

    def test_edit_export_choices(self):
        self.c.edit()
        self.assertEqual(self.c.exports.meta.elements["name"].choices, (
            'partchild1.health',
            'partchild1.inportConnector',
            'partchild1.outportConnector',
            'partchild2.health',
            'partchild2.inportConnector',
            'partchild2.outportConnector',
            'partchild3.health',
            'partchild3.inportConnector',
            'partchild3.outportConnector'))

    def test_report_ports(self):
        context = Context("c", self.p)
        ports = self.p1.report_ports(context)
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0].direction, "in")
        self.assertEqual(ports[0].type, "int32")
        self.assertEqual(ports[0].value, "")
        self.assertEqual(ports[0].extra, "")
        self.assertEqual(ports[1].direction, "out")
        self.assertEqual(ports[1].type, "int32")
        self.assertEqual(ports[1].value, "")
        self.assertEqual(ports[1].extra, "Connector")

    def test_layout(self):
        b = self.p.block_view("mainBlock")
        self.c.edit()
        self.checkState(sm.EDITABLE)

        new_layout = Table(self.c.layout.meta)
        new_layout.name = ["partchild1", "partchild2", "partchild3"]
        new_layout.mri = ["part1", "part2", "part3"]
        new_layout.x = [10, 11, 12]
        new_layout.y = [20, 21, 22]
        new_layout.visible = [True, True, True]
        b.layout.value = new_layout
        self.assertEqual(self.c.parts['partchild1'].x, 10)
        self.assertEqual(self.c.parts['partchild1'].y, 20)
        self.assertEqual(self.c.parts['partchild1'].visible, True)
        self.assertEqual(self.c.parts['partchild2'].x, 11)
        self.assertEqual(self.c.parts['partchild2'].y, 21)
        self.assertEqual(self.c.parts['partchild2'].visible, True)
        self.assertEqual(self.c.parts['partchild3'].x, 12)
        self.assertEqual(self.c.parts['partchild3'].y, 22)
        self.assertEqual(self.c.parts['partchild3'].visible, True)

        new_layout.visible = [True, False, True]
        b.layout.value = new_layout
        self.assertEqual(self.c.parts['partchild1'].visible, True)
        self.assertEqual(self.c.parts['partchild2'].visible, False)
        self.assertEqual(self.c.parts['partchild3'].visible, True)

    def test_sever_all_inports(self):
        b1, b2, b3 = (self.c1.block_view(), self.c2.block_view(),
                      self.c3.block_view())
        b1.inportConnector.value = 'Connector'
        b2.inportConnector.value = 'Connector'
        b3.inportConnector.value = 'Connector3'

        self.p1.sever_inports(b1)
        assert b1.inportConnector.value == ''
        assert b2.inportConnector.value == 'Connector'
        assert b3.inportConnector.value == 'Connector3'

    def test_sever_inports_connected_to(self):
        b1 = self.c1.block_view()

        b1.inportConnector.value = 'Connector'
        assert b1.inportConnector.value == 'Connector'

        lookup = {'Connector': 'int32'}
        self.p1.sever_inports(b1, lookup)
        assert b1.inportConnector.value == ''

    def test_load_save(self):
        b1 = self.c1.block_view()
        context = Context("c", self.p)
        structure1 = self.p1.save(context)
        expected = dict(inportConnector="")
        assert structure1 == expected
        b1.inportConnector.value = "blah"
        structure2 = self.p1.save(context)
        expected = dict(inportConnector="blah")
        assert structure2 == expected
        self.p1.load(context, dict(
            partchild1=dict(inportConnector="blah_again")))
        assert b1.inportConnector.value == "blah_again"

if __name__ == "__main__":
    unittest.main(verbosity=2)
