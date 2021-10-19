import os
import shutil
import unittest

from mock import MagicMock, call, patch

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
from malcolm.modules.builtin.controllers import (
    ManagerController,
    StatefulController,
    check_git_version,
)
from malcolm.modules.builtin.defines import tmp_dir
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.util import ExportTable, LayoutTable, ManagerStates


class TestCheckGitVersion(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_versions_are_new_enough(self, mock_check_output):
        required_version = "1.7.2"
        versions_to_check = ["2.2", "2.0alpha1", "2.16.5", "2.0.1.2"]
        try:
            for version in versions_to_check:
                mock_check_output.return_value = f"git version {version}\n".encode()
                assert check_git_version(required_version) is True
        except AssertionError:
            self.fail(f"Expected version {version} to pass check")

    @patch("subprocess.check_output")
    def test_versions_are_too_old(self, mock_check_output):
        required_version = "1.7.2"
        versions_to_check = ["1.2", "1.0alpha1", "1.6.5", "1.0.1.2"]
        try:
            for version in versions_to_check:
                mock_check_output.return_value = f"git version {version}\n".encode()
                assert check_git_version(required_version) is False
        except AssertionError:
            self.fail(f"Expected version {version} to fail check")


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

        # Create temporary config directory for ProcessController
        self.config_dir = tmp_dir("config_dir")
        self.main_block_name = "mainBlock"
        self.c = ManagerController("mainBlock", config_dir=self.config_dir.value)
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
        shutil.rmtree(self.config_dir.value)

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

    def _get_design_filename(self, block_name, design_name):
        return f"{self.config_dir.value}/{block_name}/{design_name}.json"

    def check_expected_save(
        self, design_name, x=0.0, y=0.0, visible="true", attr="defaultv"
    ):
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
        with open(self._get_design_filename(self.main_block_name, design_name)) as f:
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
        design_name = "testSaveLayout"
        b.save(designName=design_name)
        assert len(li) == 3
        assert li[0]["writeable"] is False
        assert li[1]["choices"] == ["", design_name]
        assert li[2]["writeable"] is True
        assert self.c.design.meta.choices == ["", design_name]
        self.check_expected_save(design_name)
        assert self.c.state.value == "Ready"
        assert self.c.design.value == design_name
        assert self.c.modified.value is False
        os.remove(self._get_design_filename(self.main_block_name, design_name))
        self.c_part.attr.set_value("newv")
        assert self.c.modified.value is True
        assert (
            self.c.modified.alarm.message == "part2.attr.value = 'newv' not 'defaultv'"
        )
        self.c.save(designName="")
        self.check_expected_save(design_name, attr="newv")
        design_filename = self._get_design_filename(self.main_block_name, design_name)
        assert self.c.design.value == "testSaveLayout"
        assert self.c._run_git_cmd.call_args_list == [
            call("add", design_filename),
            call(
                "commit",
                "--allow-empty",
                "-m",
                "Saved mainBlock testSaveLayout",
                design_filename,
            ),
            call("add", design_filename),
            call(
                "commit",
                "--allow-empty",
                "-m",
                "Saved mainBlock testSaveLayout",
                design_filename,
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
        design_name = "testSaveLayout"
        self.b.save(designName=design_name)
        assert self.c.modified.value is False
        self.check_expected_save(design_name, 10.0, 20.0, "false")
        self.c.parts["part2"].x = 30
        self.c.set_design(design_name)
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
