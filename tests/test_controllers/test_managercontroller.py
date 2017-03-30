import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call
from time import sleep

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.controllers.managercontroller import ManagerController
from malcolm.core import method_writeable_in, method_takes, DefaultStateMachine
from malcolm.core import Process, Part, Table, Task
from malcolm.core.syncfactory import SyncFactory
from malcolm.parts.builtin.childpart import ChildPart


class TestManagerController(unittest.TestCase):
    maxDiff = None

    def checkState(self, state, child=True, parent=True):
        if child:
            self.assertEqual(self.c_child.state.value, state)
        if parent:
            self.assertEqual(self.c.state.value, state)

    def setUp(self):
        self.p = Process('process1', SyncFactory('threading'))

        # create a child ManagerController block
        params = ManagerController.MethodMeta. \
            prepare_input_map(mri='childBlock', configDir="/tmp")
        self.c_child = ManagerController(self.p, [], params)
        self.b_child = self.c_child.block

        self.sm = self.c_child.stateMachine

        params = Part.MethodMeta.prepare_input_map(name='part1')
        part1 = Part(self.p, params)
        params = {'name': 'part2', 'mri': 'childBlock'}
        params = ChildPart.MethodMeta.prepare_input_map(**params)
        part2 = ChildPart(self.p, params)

        # create a root block for the ManagerController block to reside in
        parts = [part1, part2]
        params = ManagerController.MethodMeta.prepare_input_map(
            mri='mainBlock', configDir="/tmp")
        self.c = ManagerController(self.p, parts, params)
        self.b = self.c.block

        # check that do_initial_reset works asynchronously
        self.p.start()

        # wait until block is Ready
        task = Task("block_ready_task", self.p)
        task.when_matches(self.b["state"], self.sm.READY, timeout=1)

        self.checkState(self.sm.READY)

    def tearDown(self):
        self.p.stop()

    def test_init(self):

        # the following block attributes should be created by a call to
        # set_attributes via _set_block_children in __init__
        self.assertEqual(self.b['layout'].meta.typeid,
                         'malcolm:core/TableMeta:1.0')
        self.assertEqual(self.b['layoutName'].meta.typeid,
                         'malcolm:core/ChoiceMeta:1.0')

        # the following hooks should be created via _find_hooks in __init__
        self.assertEqual(self.c.hook_names, {
            self.c.Reset: "Reset",
            self.c.Disable: "Disable",
            self.c.Layout: "Layout",
            self.c.ReportOutports: "ReportOutports",
            self.c.Load: "Load",
            self.c.Save: "Save",
        })

        # check instantiation of object tree via logger names
        self.assertEqual(self.c._logger.name,
                         'ManagerController(mainBlock)')
        self.assertEqual(self.c.parts['part1']._logger.name,
                         'ManagerController(mainBlock).part1')
        self.assertEqual(self.c.parts['part2']._logger.name,
                         'ManagerController(mainBlock).part2')
        self.assertEqual(self.c_child._logger.name,
                         'ManagerController(childBlock)')

    def test_edit(self):
        structure = MagicMock()
        self.c.load_structure = structure
        self.c.edit()
        # editing only affects one level
        self.checkState(self.sm.EDITABLE, child=False)
        self.assertEqual(self.c.load_structure, structure)

    def test_edit_exception(self):
        self.c.edit()
        with self.assertRaises(Exception):
            self.c.edit()

    def check_expected_save(self, x=0.0, y=0.0, visible="false"):
        expected = [x.strip() for x in ("""{
          "layout": {
            "part2": {
              "x": %s,
              "y": %s,
              "visible": %s
            }
          },
          "part2": {}
        }""" % (x, y, visible)).splitlines()]
        actual = [x.strip() for x in open(
            "/tmp/mainBlock/testSaveLayout.json").readlines()]
        self.assertEqual(actual, expected)

    def test_save(self):
        self.c.edit()
        params = {'layoutName': 'testSaveLayout'}
        params = ManagerController.save.MethodMeta.prepare_input_map(**params)
        self.c.save(params)
        self.check_expected_save()
        self.checkState(self.sm.AFTER_RESETTING, child=False)
        self.assertEqual(self.c.layout_name.value, 'testSaveLayout')
        os.remove("/tmp/mainBlock/testSaveLayout.json")
        self.c.edit()
        params = {'layoutName': None}
        params = ManagerController.save.MethodMeta.prepare_input_map(**params)
        self.c.save(params)
        self.check_expected_save()
        self.assertEqual(self.c.layout_name.value, 'testSaveLayout')

    def move_child_block(self):
        self.assertEqual(self.b.layout.x, [0])
        new_layout = Table(self.c.layout.meta)
        new_layout.name = ["part2"]
        new_layout.mri = ["P45-MRI"]
        new_layout.x = [10]
        new_layout.y = [20]
        new_layout.visible = [True]
        self.b.layout = new_layout
        self.assertEqual(self.b.layout.x, [10])

    def test_move_child_block_dict(self):
        self.b.edit()
        self.assertEqual(self.b.layout.x, [0])
        new_layout = dict(
            name=["part2"],
            mri=[""],
            x=[10],
            y=[20],
            visible=[True])
        self.b.layout = new_layout
        self.assertEqual(self.b.layout.x, [10])

    def test_revert(self):
        self.c.edit()
        self.move_child_block()
        self.assertEqual(self.b.layout.x, [10])
        self.c.revert()
        self.assertEqual(self.b.layout.x, [0])
        self.checkState(self.sm.AFTER_RESETTING, child=False)

    def test_set_and_load_layout(self):
        self.c.edit()
        self.checkState(self.sm.EDITABLE, child=False)

        new_layout = Table(self.c.layout.meta)
        new_layout.name = ["part2"]
        new_layout.mri = ["P45-MRI"]
        new_layout.x = [10]
        new_layout.y = [20]
        new_layout.visible = [True]
        self.b.layout = new_layout
        self.assertEqual(self.c.parts['part2'].x, 10)
        self.assertEqual(self.c.parts['part2'].y, 20)
        self.assertEqual(self.c.parts['part2'].visible, True)

        # save the layout, modify and restore it
        params = {'layoutName': 'testSaveLayout'}
        params = ManagerController.save.MethodMeta.prepare_input_map(**params)
        self.c.save(params)
        self.check_expected_save(10.0, 20.0, "true")

        self.c.parts['part2'].x = 30
        self.b.layoutName = 'testSaveLayout'
        self.assertEqual(self.c.parts['part2'].x, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
