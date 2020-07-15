import os
import shutil
import unittest

from mock import MagicMock, call

from malcolm.compat import OrderedDict
from malcolm.core import (
    Context,
    Part,
    PartRegistrar,
    Process,
    StringMeta,
    Widget,
    config_tag,
)
from malcolm.modules.builtin.controllers import ManagerController, StatefulController
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable, LayoutTable, ManagerStates


class TestManagerStates(unittest.TestCase):
    def setUp(self):
        self.o = ManagerStates()

    def test_init(self):
        expected = OrderedDict()
        expected["Resetting"] = {"Ready", "Fault", "Disabling"}
        expected["Ready"] = {"Saving", "Fault", "Disabling", "Loading"}
        expected["Saving"] = {"Fault", "Ready", "Disabling"}
        expected["Loading"] = {"Disabling", "Fault", "Ready"}
        expected["Fault"] = {"Resetting", "Disabling"}
        expected["Disabling"] = {"Disabled", "Fault"}
        expected["Disabled"] = {"Resetting"}
        assert self.o._allowed == expected


class MyPart(Part):
    attr = None

    def setup(self, registrar: PartRegistrar) -> None:
        self.attr = StringMeta(
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model("defaultv")
        registrar.add_attribute_model("attr", self.attr, self.attr.set_value)


class TestManagerController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.p = Process("process1")

        # create a child to client
        self.c_child = StatefulController("childBlock")
        self.c_part = MyPart("cp1")
        self.c_child.add_part(self.c_part)
        self.p.add_controller(self.c_child)

        # create a root block for the ManagerController block to reside in
        if os.path.isdir("/tmp/mainBlock"):
            shutil.rmtree("/tmp/mainBlock")
        self.c = ManagerController("mainBlock", config_dir="/tmp")
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
        assert self.c.layout.value.x == [0.0]
        assert self.c.layout.value.y == [0.0]
        assert self.c.layout.value.visible == [True]
        assert self.c.layout.meta.elements["name"].writeable is False
        assert self.c.layout.meta.elements["mri"].writeable is False
        assert self.c.layout.meta.elements["x"].writeable is True
        assert self.c.layout.meta.elements["y"].writeable is True
        assert self.c.layout.meta.elements["visible"].writeable is True
        assert self.c.design.value == ""
        assert self.c.exports.value.source == []
        assert self.c.exports.meta.elements["source"].choices == [
            "part2.health",
            "part2.state",
            "part2.disable",
            "part2.reset",
            "part2.attr",
        ]
        assert self.c.exports.value.export == []
        assert self.c.modified.value is False
        assert self.c.modified.alarm.message == ""
        assert self.b.mri.value == "mainBlock"
        assert self.b.mri.meta.tags == ["sourcePort:block:mainBlock"]

    def check_expected_save(self, x=0.0, y=0.0, visible="true", attr="defaultv"):
        expected = [
            x.strip()
            for x in (
                """{
          "attributes": {
             "layout": {
               "part2": {
                 "x": %s,
                 "y": %s,
                 "visible": %s
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
        }"""
                % (x, y, visible, attr)
            ).splitlines()
        ]
        with open("/tmp/mainBlock/testSaveLayout.json") as f:
            actual = [x.strip() for x in f.readlines()]
        assert actual == expected

    def test_save(self):
        self.c._run_git_cmd = MagicMock()
        assert self.c.design.value == ""
        assert self.c.design.meta.choices == [""]
        c = Context(self.p)
        li = []
        c.subscribe(["mainBlock", "design", "meta"], li.append)
        # Wait for long enough for the other process to get a look in
        c.sleep(0.1)
        assert len(li) == 1
        assert li.pop()["choices"] == [""]
        b = c.block_view("mainBlock")
        b.save(designName="testSaveLayout")
        assert len(li) == 3
        assert li[0]["writeable"] is False
        assert li[1]["choices"] == ["", "testSaveLayout"]
        assert li[2]["writeable"] is True
        assert self.c.design.meta.choices == ["", "testSaveLayout"]
        self.check_expected_save()
        assert self.c.state.value == "Ready"
        assert self.c.design.value == "testSaveLayout"
        assert self.c.modified.value is False
        os.remove("/tmp/mainBlock/testSaveLayout.json")
        self.c_part.attr.set_value("newv")
        assert self.c.modified.value is True
        assert (
            self.c.modified.alarm.message == "part2.attr.value = 'newv' not 'defaultv'"
        )
        self.c.save(designName="")
        self.check_expected_save(attr="newv")
        assert self.c.design.value == "testSaveLayout"
        assert self.c._run_git_cmd.call_args_list == [
            call("add", "/tmp/mainBlock/testSaveLayout.json"),
            call(
                "commit",
                "--allow-empty",
                "-m",
                "Saved mainBlock testSaveLayout",
                "/tmp/mainBlock/testSaveLayout.json",
            ),
            call("add", "/tmp/mainBlock/testSaveLayout.json"),
            call(
                "commit",
                "--allow-empty",
                "-m",
                "Saved mainBlock testSaveLayout",
                "/tmp/mainBlock/testSaveLayout.json",
            ),
        ]

    def move_child_block(self):
        new_layout = dict(
            name=["part2"], mri=["anything"], x=[10], y=[20], visible=[True]
        )
        self.b.layout.put_value(new_layout)

    def test_move_child_block_dict(self):
        assert self.b.layout.value.x == [0]
        self.move_child_block()
        assert self.b.layout.value.x == [10]

    def test_set_and_load_layout(self):
        new_layout = LayoutTable(
            name=["part2"], mri=["anything"], x=[10], y=[20], visible=[False]
        )
        self.c.set_layout(new_layout)
        assert self.c.parts["part2"].x == 10
        assert self.c.parts["part2"].y == 20
        assert self.c.parts["part2"].visible is False
        assert self.c.modified.value is True
        assert self.c.modified.alarm.message == "layout changed"

        # save the layout, modify and restore it
        self.b.save(designName="testSaveLayout")
        assert self.c.modified.value is False
        self.check_expected_save(10.0, 20.0, "false")
        self.c.parts["part2"].x = 30
        self.c.set_design("testSaveLayout")
        assert self.c.parts["part2"].x == 10

    def test_set_export_parts(self):
        context = Context(self.p)
        b = context.block_view("mainBlock")
        assert list(b) == [
            "meta",
            "health",
            "state",
            "disable",
            "reset",
            "mri",
            "layout",
            "design",
            "exports",
            "modified",
            "save",
            "attr",
        ]
        assert b.attr.meta.tags == ["widget:textinput"]
        new_exports = ExportTable.from_rows(
            [("part2.attr", "childAttr"), ("part2.reset", "childReset")]
        )
        self.c.set_exports(new_exports)
        assert self.c.modified.value is True
        assert self.c.modified.alarm.message == "exports changed"
        self.c.save(designName="testSaveLayout")
        assert self.c.modified.value is False
        # block has changed, get a new view
        b = context.block_view("mainBlock")
        assert list(b) == [
            "meta",
            "health",
            "state",
            "disable",
            "reset",
            "mri",
            "layout",
            "design",
            "exports",
            "modified",
            "save",
            "attr",
            "childAttr",
            "childReset",
        ]
        assert self.c.state.value == "Ready"
        assert b.childAttr.value == "defaultv"
        assert self.c.modified.value is False
        m = MagicMock()
        b.childAttr.subscribe_value(m)
        # allow a subscription to come through
        context.sleep(0.1)
        m.assert_called_once_with("defaultv")
        m.reset_mock()
        self.c_part.attr.set_value("newv")
        assert b.childAttr.value == "newv"
        assert self.c_part.attr.value == "newv"
        assert self.c.modified.value is True
        assert (
            self.c.modified.alarm.message == "part2.attr.value = 'newv' not 'defaultv'"
        )
        # allow a subscription to come through
        context.sleep(0.1)
        m.assert_called_once_with("newv")
        b.childAttr.put_value("again")
        assert b.childAttr.value == "again"
        assert self.c_part.attr.value == "again"
        assert self.c.modified.value is True
        assert (
            self.c.modified.alarm.message == "part2.attr.value = 'again' not 'defaultv'"
        )
        # remove the field
        new_exports = ExportTable([], [])
        self.c.set_exports(new_exports)
        assert self.c.modified.value is True
        self.c.save()
        assert self.c.modified.value is False
        # block has changed, get a new view
        b = context.block_view("mainBlock")
        assert "childAttr" not in b
