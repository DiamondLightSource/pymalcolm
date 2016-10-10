from collections import OrderedDict, namedtuple
import json

from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import ManagerStateMachine, method_writeable_in, method_takes, \
    Hook, Table
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, \
    BooleanArrayMeta, TableMeta, StringMeta


sm = ManagerStateMachine

# A class to hold the information about the layout of a part
PartLayout = namedtuple("PartLayout", "mri,x,y,visible")

# Ac class to hold the information about the outports of a part
PartOutports = namedtuple("PartOutports", "types,values")


@sm.insert
@method_takes()
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # hooks
    UpdateLayout = Hook()
    ListOutports = Hook()
    LoadLayout = Hook()
    SaveLayout = Hook()

    # default attributes
    layout = None
    layout_name = None

    # state to revert to
    revert_structure = None

    def create_attributes(self):
        for data in super(ManagerController, self).create_attributes():
            yield data
        # Make a table for the layout info we need
        columns = OrderedDict()
        columns["name"] = StringArrayMeta("Name of layout part")
        columns["mri"] = StringArrayMeta("Malcolm full name of child block")
        columns["x"] = NumberArrayMeta("float64", "X Coordinate of child block")
        columns["y"] = NumberArrayMeta("float64", "Y Coordinate of child block")
        columns["visible"] = BooleanArrayMeta("Whether child block is visible")
        layout_table_meta = TableMeta("Layout of child blocks", columns=columns)
        layout_table_meta.set_writeable_in(sm.EDITING)
        self.layout = layout_table_meta.make_attribute()
        yield "layout", self.layout, self.set_layout
        self.layout_name = StringMeta(
            "Saved layout name to load").make_attribute()
        self.layout_name.meta.set_writeable_in(sm.EDITING)
        yield "layoutName", self.layout_name, self.load_layout

    def do_reset(self):
        super(ManagerController, self).do_reset()
        self.set_layout(Table(self.layout.meta))

    @method_writeable_in(sm.EDITABLE)
    def edit(self):
        try:
            self.transition(sm.EDITING, "Editing")
            self.do_edit()
            self.transition(sm.EDITABLE, "Now Editable")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Editing")
            self.transition(sm.FAULT, str(e))
            raise

    def do_edit(self):
        self.revert_structure = self._save_to_structure()

    @method_writeable_in(sm.EDITABLE)
    @method_takes(
        "layoutName", StringMeta(
            "Name of layout to save to, if different from current layoutName"),
        None)
    def save(self, params):
        try:
            self.transition(sm.SAVING, "Saving")
            self.do_save(params.layoutName)
            self.transition(self.stateMachine.AFTER_RESETTING, "Done Saving")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Saving")
            self.transition(sm.FAULT, str(e))
            raise

    def do_save(self, layout_name=None):
        if layout_name is None:
            layout_name = self.layout_name.value
        structure = self._save_to_structure()
        filename = "/tmp/" + layout_name + ".json"
        text = json.dumps(structure, indent="  ")
        open(filename, "w").write(text)
        self.layout_name.set_value(layout_name)

    @method_writeable_in(sm.EDITABLE)
    def revert(self):
        try:
            self.transition(sm.REVERTING, "Reverting")
            self.do_revert()
            self.transition(self.stateMachine.AFTER_RESETTING, "Done Reverting")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Reverting")
            self.transition(sm.FAULT, str(e))
            raise

    def do_revert(self):
        self._load_from_structure(self.revert_structure)

    def load_layout(self, value):
        # TODO: Look for value in our save file location
        filename = "/tmp/" + value + ".json"
        structure = json.loads(filename)
        self._load_from_structure(structure)
        self.layout_name.set_value(value)

    def _save_to_structure(self):
        structure = self.run_hook(
            self.SaveLayout, self.create_part_tasks())
        structure["layout"] = self.layout.value
        return structure

    def _load_from_structure(self, structure):
        self.set_layout(structure["layout"])
        self.run_hook(
            self.LoadLayout, self.create_part_tasks(), structure)

    def set_layout(self, value):
        part_outports = self.run_hook(
            self.ListOutports, self.create_part_tasks())
        part_layouts = self.run_hook(
            self.UpdateLayout, self.create_part_tasks(), part_outports, value)
        layout_table = Table(self.layout.meta)
        for name, part_layout in part_layouts.items():
            layout_table.append((name,) + part_layout)
        self.layout.set_value(layout_table)
