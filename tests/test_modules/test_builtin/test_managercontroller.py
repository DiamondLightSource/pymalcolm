import unittest
from mock import MagicMock
import os

# module imports
from malcolm.compat import OrderedDict
from malcolm.modules.builtin.controllers import StatefulController, \
    ManagerController, ManagerStates
from malcolm.core import Process, Part, Table, Context, call_with_params
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.modules.builtin.parts import ChildPart


class TestManagerStates(unittest.TestCase):

    def setUp(self):
        self.o = ManagerStates()

    def test_init(self):
        expected = OrderedDict()
        expected['Resetting'] = {'Ready', 'Fault', 'Disabling'}
        expected['Ready'] = {'Saving', "Fault", "Disabling", "Loading"}
        expected['Saving'] = {'Fault', 'Ready', 'Disabling'}
        expected['Loading'] = {'Disabling', 'Fault', 'Ready'}
        expected['Fault'] = {"Resetting", "Disabling"}
        expected['Disabling'] = {"Disabled", "Fault"}
        expected['Disabled'] = {"Resetting"}
        assert self.o._allowed == expected


class MyPart(Part):
    def create_attributes(self):
        self.attr = StringMeta(tags=["config"]).create_attribute("defaultv")
        yield "attr", self.attr, self.attr.set_value


class TestManagerController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.p = Process('process1')

        # create a child to client
        self.c_part = MyPart("cp1")
        self.c_child = call_with_params(
            StatefulController, self.p, [self.c_part], mri="childBlock")
        self.p.add_controller("childBlock", self.c_child)

        part1 = Part("part1")
        part2 = call_with_params(ChildPart, name='part2', mri='childBlock')

        # create a root block for the ManagerController block to reside in
        parts = [part1, part2]
        self.c = call_with_params(
            ManagerController, self.p, parts, mri='mainBlock', configDir="/tmp")
        self.p.add_controller("mainBlock", self.c)

        # check that do_initial_reset works asynchronously
        assert self.c.state.value == "Disabled"
        self.p.start()
        assert self.c.state.value == "Ready"

    def tearDown(self):
        self.p.stop()

    def test_init(self):
        assert self.c.layout.value.name == ("part2",)
        assert self.c.layout.value.mri == ("childBlock",)
        assert self.c.layout.value.x == [0.0]
        assert self.c.layout.value.y == [0.0]
        assert self.c.layout.value.visible == [True]
        assert self.c.design.value == ""
        assert self.c.exports.value.name == ()
        assert self.c.exports.meta.elements["name"].choices == \
               ('part2.health', 'part2.state', 'part2.disable', 'part2.reset',
                'part2.attr')
        assert self.c.exports.value.exportName == ()
        assert self.c.modified.value == False
        assert self.c.modified.alarm.message == ""

    def check_expected_save(self, x=0.0, y=0.0, visible="true", attr="defaultv"):
        expected = [x.strip() for x in ("""{
          "layout": {
            "part2": {
              "x": %s,
              "y": %s,
              "visible": %s
            }
          },
          "exports": {},
          "part2": {
            "attr": "%s"
          }
        }""" % (x, y, visible, attr)).splitlines()]
        actual = [x.strip() for x in open(
            "/tmp/mainBlock/testSaveLayout.json").readlines()]
        self.assertEqual(actual, expected)

    def test_save(self):
        call_with_params(self.c.save, design="testSaveLayout")
        self.check_expected_save()
        assert self.c.state.value == "Ready"
        assert self.c.design.value == 'testSaveLayout'
        assert self.c.modified.value == False
        os.remove("/tmp/mainBlock/testSaveLayout.json")
        self.c_part.attr.set_value("newv")
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == \
               "part2.attr.value = 'newv' not 'defaultv'"
        call_with_params(self.c.save, design="")
        self.check_expected_save(attr="newv")
        assert self.c.design.value == 'testSaveLayout'

    def move_child_block(self):
        new_layout = Table(self.c.layout.meta)
        new_layout.name = ["part2"]
        new_layout.mri = ["anything"]
        new_layout.x = [10]
        new_layout.y = [20]
        new_layout.visible = [True]
        self.c.set_layout(new_layout)

    def test_move_child_block_dict(self):
        assert self.c.layout.value.x == [0]
        new_layout = dict(
            name=["part2"],
            mri=["anything"],
            x=[10],
            y=[20],
            visible=[True])
        self.c.set_layout(new_layout)
        assert self.c.layout.value.x == [10]

    def test_set_and_load_layout(self):
        new_layout = Table(self.c.layout.meta)
        new_layout.name = ["part2"]
        new_layout.mri = ["anything"]
        new_layout.x = [10]
        new_layout.y = [20]
        new_layout.visible = [False]
        self.c.set_layout(new_layout)
        assert self.c.parts['part2'].x == 10
        assert self.c.parts['part2'].y == 20
        assert self.c.parts['part2'].visible == False
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == "layout changed"

        # save the layout, modify and restore it
        call_with_params(self.c.save, design='testSaveLayout')
        assert self.c.modified.value == False
        self.check_expected_save(10.0, 20.0, "false")
        self.c.parts['part2'].x = 30
        self.c.set_design('testSaveLayout')
        self.assertEqual(self.c.parts['part2'].x, 10)

    def test_set_export_parts(self):
        context = Context(self.p)
        b = context.block_view("mainBlock")
        assert list(b) == [
            'meta',
            'health',
            'state',
            'layout',
            'design',
            'exports',
            'modified',
            'disable',
            'reset',
            'save']
        new_exports = Table(self.c.exports.meta)
        new_exports.append(('part2.attr', 'childAttr'))
        new_exports.append(('part2.reset', 'childReset'))
        self.c.set_exports(new_exports)
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == "exports changed"
        call_with_params(self.c.save, design='testSaveLayout')
        assert self.c.modified.value == False
        # block has changed, get a new view
        b = context.block_view("mainBlock")
        assert list(b) == [
            'meta',
            'health',
            'state',
            'layout',
            'design',
            'exports',
            'modified',
            'disable',
            'reset',
            'save',
            'childAttr',
            'childReset']
        assert self.c.state.value == "Ready"
        assert b.childAttr.value == "defaultv"
        assert self.c.modified.value == False
        m = MagicMock()
        f = b.childAttr.subscribe_value(m)
        self.c_part.attr.set_value("newv")
        assert b.childAttr.value == "newv"
        assert self.c_part.attr.value == "newv"
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == \
               "part2.attr.value = 'newv' not 'defaultv'"
        # allow a subscription to come through
        context.unsubscribe(f)
        context.wait_all_futures(f)
        m.assert_called_once_with("newv")
        b.childAttr.put_value("again")
        assert b.childAttr.value == "again"
        assert self.c_part.attr.value == "again"
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == \
               "part2.attr.value = 'again' not 'defaultv'"
        # remove the field
        new_exports = Table(self.c.exports.meta)
        self.c.set_exports(new_exports)
        assert self.c.modified.value == True
        call_with_params(self.c.save)
        assert self.c.modified.value == False
        # block has changed, get a new view
        b = context.block_view("mainBlock")
        assert "childAttr" not in b

if __name__ == "__main__":
    unittest.main(verbosity=2)
