import unittest
from mock import MagicMock, call
import os

from malcolm.compat import OrderedDict
from malcolm.modules.builtin.controllers import StatefulController, \
    ManagerController
from malcolm.modules.builtin.util import ManagerStates, LayoutTable, ExportTable
from malcolm.core import Process, Part, Table, Context, PartRegistrar, \
    StringMeta, config_tag, Widget, json_decode, json_encode
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
    attr = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.attr = StringMeta(tags=[config_tag(), Widget.TEXTINPUT.tag()]
                               ).create_attribute_model("defaultv")
        registrar.add_attribute_model("attr", self.attr, self.attr.set_value)


class TestManagerController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.p = Process('process1')

        # create a child to client
        self.c_child = StatefulController("childBlock")
        self.c_part = MyPart("cp1")
        self.c_child.add_part(self.c_part)
        self.p.add_controller(self.c_child)

        # create a root block for the ManagerController block to reside in
        self.c = ManagerController('mainBlock', config_dir="/tmp")
        self.c.add_part(MyPart("part1"))
        self.c.add_part(ChildPart("part2", mri="childBlock", initial_visibility=True))
        self.p.add_controller(self.c)
        self.b = self.p.block_view("mainBlock")

        # check that do_initial_reset works asynchronously
        assert self.c.state.value == "Disabled"
        self.p.start()
        assert self.c.state.value == "Ready"

    def tearDown(self):
        self.p.stop(timeout=1)

    def test_init(self):
        assert self.c.layout.value.name == ["part2"]
        assert self.c.layout.value.mri == ["childBlock"]
        assert self.c.layout.value.presentation == [""]
        assert self.c.layout.value.visible == [True]
        assert self.c.design.value == ""
        assert self.c.exports.value.source == []
        assert self.c.exports.meta.elements["source"].choices == \
               ['part2.health', 'part2.state', 'part2.disable', 'part2.reset',
                'part2.attr']
        assert self.c.exports.value.export == []
        assert self.c.modified.value is False
        assert self.c.modified.alarm.message == ""

    def check_expected_save(self, visible="true", presentation='""',
                            attr="defaultv"):
        expected = [x.strip() for x in ("""{
          "attributes": {
             "layout": {
               "part2": {
                 "visible": %s,
                 "presentation": %s  
               }
             },
             "exports": {},
             "attr": "defaultv"
          },
          "children": {
             "part2": {
               "attr": "%s"
             }
          }
        }""" % (visible, presentation, attr)).splitlines()]
        with open("/tmp/mainBlock/testSaveLayout.json") as f:
            actual = [x.strip() for x in f.readlines()]
        assert actual == expected

    def test_save(self):
        self.c._run_git_cmd = MagicMock()
        self.c.save(design="testSaveLayout")
        self.check_expected_save()
        assert self.c.state.value == "Ready"
        assert self.c.design.value == 'testSaveLayout'
        assert self.c.modified.value is False
        os.remove("/tmp/mainBlock/testSaveLayout.json")
        self.c_part.attr.set_value("newv")
        assert self.c.modified.value is True
        assert self.c.modified.alarm.message == \
               "part2.attr.value = 'newv' not 'defaultv'"
        self.c.save(design="")
        self.check_expected_save(attr="newv")
        assert self.c.design.value == 'testSaveLayout'
        assert self.c._run_git_cmd.call_args_list == [
            call('add', '/tmp/mainBlock/testSaveLayout.json'),
            call('commit', '--allow-empty', '-m',
                 'Saved mainBlock testSaveLayout',
                 '/tmp/mainBlock/testSaveLayout.json'),
            call('add', '/tmp/mainBlock/testSaveLayout.json'),
            call('commit', '--allow-empty', '-m',
                 'Saved mainBlock testSaveLayout',
                 '/tmp/mainBlock/testSaveLayout.json')]

    def move_child_block(self):
        new_layout = dict(
            name=["part2"],
            mri=["anything"],
            presentation=['{"x": 10.0, "y": 20.0}'],
            visible=[True])
        self.b.layout.put_value(new_layout)

    def test_move_child_block_dict(self):
        assert self.b.layout.value.presentation == [""]
        self.move_child_block()
        assert json_decode(self.b.layout.value.presentation[0])["x"] == 10
        self.b.save(design='testSaveLayout')
        self.check_expected_save("true", '{\n"x": 10.0,\n"y": 20.0\n}')

    def test_set_and_load_layout(self):
        new_layout = LayoutTable(
            name=["part2"], mri=["anything"], visible=[False],
            presentation=[""])
        self.c.set_layout(new_layout)
        assert self.c.parts['part2'].presentation == ""
        assert self.c.parts['part2'].visible == False
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == "layout changed"

        # save the layout, modify and restore it
        self.b.save(design='testSaveLayout')
        assert self.c.modified.value is False
        self.check_expected_save("false")
        self.c.parts['part2'].presentation = "blah"
        self.c.set_design('testSaveLayout')
        assert self.c.parts['part2'].presentation == ""

    def test_set_export_parts(self):
        context = Context(self.p)
        b = context.block_view("mainBlock")
        assert list(b) == [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'layout',
            'design',
            'exports',
            'modified',
            'save',
            'attr']
        assert b.attr.meta.tags == ["widget:textinput"]
        new_exports = ExportTable.from_rows([
            ('part2.attr', 'childAttr'),
            ('part2.reset', 'childReset')
        ])
        self.c.set_exports(new_exports)
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == "exports changed"
        self.c.save(design='testSaveLayout')
        assert self.c.modified.value == False
        # block has changed, get a new view
        b = context.block_view("mainBlock")
        assert list(b) == [
            'meta',
            'health',
            'state',
            'disable',
            'reset',
            'layout',
            'design',
            'exports',
            'modified',
            'save',
            'attr',
            'childAttr',
            'childReset']
        assert self.c.state.value == "Ready"
        assert b.childAttr.value == "defaultv"
        assert self.c.modified.value == False
        m = MagicMock()
        f = b.childAttr.subscribe_value(m)
        # allow a subscription to come through
        context.sleep(0.1)
        m.assert_called_once_with("defaultv")
        m.reset_mock()
        self.c_part.attr.set_value("newv")
        assert b.childAttr.value == "newv"
        assert self.c_part.attr.value == "newv"
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == \
               "part2.attr.value = 'newv' not 'defaultv'"
        # allow a subscription to come through
        context.sleep(0.1)
        m.assert_called_once_with("newv")
        b.childAttr.put_value("again")
        assert b.childAttr.value == "again"
        assert self.c_part.attr.value == "again"
        assert self.c.modified.value == True
        assert self.c.modified.alarm.message == \
               "part2.attr.value = 'again' not 'defaultv'"
        # remove the field
        new_exports = ExportTable([], [])
        self.c.set_exports(new_exports)
        assert self.c.modified.value == True
        self.c.save()
        assert self.c.modified.value == False
        # block has changed, get a new view
        b = context.block_view("mainBlock")
        assert "childAttr" not in b
