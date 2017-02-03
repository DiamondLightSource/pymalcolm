import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, call, ANY
from time import sleep

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.part import Part
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.core.syncfactory import SyncFactory
from malcolm.core import Process, Table, Task
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core.vmetas.stringmeta import StringMeta
from malcolm.compat import OrderedDict

sm = RunnableController.stateMachine


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
        # note 4th part of inport tag is its disconnected value
        # TODO this is yet to be documented
        in_tag = "inport:pos:"
        in_name = "inport%s" % self.name
        in_port = StringMeta(in_name, [in_tag, "config"]).make_attribute()
        in_port.meta.set_writeable_in(sm.READY)
        yield in_name, in_port, in_port.set_value

        out_name = "outport%s" % self.name
        out_tag = "outport:pos:%s" %self.name
        out_port = StringMeta(in_name, [out_tag]).make_attribute()
        out_port.meta.set_writeable_in(sm.READY)
        yield out_name, out_port, out_port.set_value


class TestChildPart(unittest.TestCase):

    def checkState(self, state):
        self.assertEqual(self.c.state.value, state)

    def makeChildBlock(self, blockMri):
        params = PortsPart.MethodMeta.prepare_input_map(name='Connector')
        port_part = PortsPart(self.p, params)

        partName = 'part%s' % blockMri
        params = DefaultController.MethodMeta.prepare_input_map(mri=blockMri)
        controller = DefaultController(self.p, [port_part], params)

        params = ChildPart.MethodMeta.prepare_input_map(
            mri=blockMri, name=partName)
        part = ChildPart(self.p, params)

        return part, controller

    def setUp(self):
        self.p = Process('process1', SyncFactory('threading'))

        self.p1, self.c1 = self.makeChildBlock('child1')
        self.p2, self.c2 = self.makeChildBlock('child2')
        self.p3, self.c3 = self.makeChildBlock('child3')

        # create a root block for the child blocks to reside in
        parts = [self.p1, self.p2, self.p3]
        params = RunnableController.MethodMeta.prepare_input_map(
            mri='mainBlock', configDir="/tmp")
        self.c = RunnableController(self.p, parts, params)
        self.b = self.c.block

        params = ChildPart.MethodMeta.prepare_input_map(
            mri='mainBlock', name='mainPart')
        self.part = ChildPart(self.p, params)

        # Get the parent block into idle state
        self.p.start()

        # wait until block is Ready
        task = Task("block_ready_task", self.p)
        task.when_matches(self.c.block["state"], sm.IDLE, timeout=1)

        self.checkState(sm.IDLE)

    def tearDown(self):
        self.p.stop()

    def test_init(self):
        # check instantiation of object tree via logger names
        self.assertEqual(self.c._logger.name,
                         'RunnableController(mainBlock)')
        self.assertEqual(self.c.parts['partchild1']._logger.name,
                         'RunnableController(mainBlock).partchild1')
        self.assertEqual(self.c.parts['partchild2']._logger.name,
                         'RunnableController(mainBlock).partchild2')
        self.assertEqual(self.c.parts['partchild3']._logger.name,
                         'RunnableController(mainBlock).partchild3')

        self.assertEqual(self.c1.parts['Connector']._logger.name,
                         'DefaultController(child1).Connector')
        self.assertEqual(self.c2.parts['Connector']._logger.name,
                         'DefaultController(child2).Connector')
        self.assertEqual(self.c3.parts['Connector']._logger.name,
                         'DefaultController(child3).Connector')

        self.assertEqual(self.c1.block.inportConnector, '')
        self.assertEqual(self.c1.block.outportConnector, '')

    def test_reset(self):
        # TODO cover the clause 'state == RESETTING'
        self.c.disable()
        self.checkState(sm.DISABLED)
        self.c.reset()
        self.checkState(sm.IDLE)

    def test_pre_layout(self):
        outports = self.p1.pre_layout(None)
        self.assertEqual(len(outports), 1)

    def test_layout(self):
        self.c.edit()
        self.checkState(sm.EDITABLE)

        new_layout = Table(self.c.layout.meta)
        new_layout.name = ["partchild1", "partchild2", "partchild3"]
        new_layout.mri = ["part1", "part2", "part3"]
        new_layout.x = [10, 11, 12]
        new_layout.y = [20, 21, 22]
        new_layout.visible = [True, True, True]
        self.b.layout = new_layout
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
        self.b.layout= new_layout
        self.assertEqual(self.c.parts['partchild1'].visible, True)
        self.assertEqual(self.c.parts['partchild2'].visible, False)
        self.assertEqual(self.c.parts['partchild3'].visible, True)

    def test_sever_all_inports(self):
        self.c1.block.inportConnector = 'Connector'
        self.c2.block.inportConnector = 'Connector'
        self.c3.block.inportConnector = 'Connector3'

        task = Task("Task1" , self.p)
        self.p1.sever_all_inports(task)
        task.wait_all([],5)
        self.assertEqual(self.c1.block.inportConnector, '')
        self.assertEqual(self.c2.block.inportConnector, 'Connector')
        self.assertEqual(self.c3.block.inportConnector, 'Connector3')

    def test_sever_inports_connected_to(self):
        self.c1.block.inportConnector = 'Connector'

        self.assertEqual(self.c1.block.inportConnector, 'Connector')

        task = Task("Task1" , self.p)
        out_port = {'Connector': 'pos'}
        self.p1.sever_inports_connected_to(task, out_port)
        self.assertEqual(self.c1.block.inportConnector, '')

    def test_get_flowgraph_ports(self):
        count = len(self.p1._get_flowgraph_ports('out'))
        self.assertEqual(count, 1)
        count = len(self.p1._get_flowgraph_ports('in'))
        self.assertEqual(count, 1)

    def test_load_save(self):
        structure1 = self.p1.save(ANY)
        expected = dict(inportConnector="")
        self.assertEqual(structure1, expected)
        self.p1.child.inportConnector = "blah"
        structure2 = self.p1.save(ANY)
        expected = dict(inportConnector="blah")
        self.assertEqual(structure2, expected)
        task = Mock()
        task.put_async.return_value = ["future"]
        self.p1.load(task, dict(partchild1=dict(inportConnector="blah_again")))
        task.put_async.assert_called_once_with(
            self.p1.child["inportConnector"], "blah_again")
        task.wait_all.assert_called_once_with(["future"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
