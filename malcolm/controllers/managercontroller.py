import json

from malcolm.compat import OrderedDict
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import ManagerStateMachine, method_writeable_in, method_takes, \
    Hook, Table, Info
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, \
    BooleanArrayMeta, TableMeta, StringMeta


class LayoutInfo(Info):
    """Info about the position and visibility of a child block in a layout

    Args:
        mri (str): Malcolm full name of child block
        x (float): X Coordinate of child block
        y (float): Y Coordinate of child block
        visible (bool): Whether child block is visible
    """
    def __init__(self, mri, x, y, visible):
        self.mri = mri
        self.x = x
        self.y = y
        self.visible = visible


sm = ManagerStateMachine


@method_takes()
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # The stateMachine that this controller implements
    stateMachine = sm()

    ReportOutports = Hook()
    """Called before Layout to get outport info from children

    Args:
        task (Task): The task used to perform operations on child blocks

    Returns:
        [OutportInfo]: the type and value of each outport of the child
    """

    Layout = Hook()
    """Called when layout table set and at init to update child layout

    Args:
        task (Task): The task used to perform operations on child blocks
        part_info (dict): {part_name: [Info]} returned from Layout hook
        layout_table (Table): A possibly partial set of changes to the layout
            table that should be acted on

    Returns:
        [LayoutInfo]: the child layout resulting from this change
    """

    Load = Hook()
    """Called at load() or revert() to load child settings from a structure

    Args:
        task (Task): The task used to perform operations on child blocks
        structure (dict): {part_name: part_structure} where part_structure is
            the return from Save hook
    """

    Save = Hook()
    """Called at save() to serialize child settings into a dict structure

    Args:
        task (Task): The task used to perform operations on child blocks
        structure (dict): {part_name: part_structure} where part_structure is
            the return from Save hook
    """

    # attributes
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
        layout_table_meta.set_writeable_in(sm.EDITABLE)
        self.layout = layout_table_meta.make_attribute()
        yield "layout", self.layout, self.set_layout
        self.layout_name = StringMeta(
            "Saved layout name to load").make_attribute()
        self.layout_name.meta.set_writeable_in(sm.EDITABLE)
        yield "layoutName", self.layout_name, self.load_layout

    def set_layout(self, value):
        part_info = self.run_hook(self.ReportOutports, self.create_part_tasks())
        part_info = self.run_hook(
            self.Layout, self.create_part_tasks(), part_info, value)
        layout_table = Table(self.layout.meta)
        for name, layout_infos in LayoutInfo.filter(part_info).items():
            assert len(layout_infos) == 1, \
                "%s returned more than 1 layout infos" % name
            layout_info = layout_infos[0]
            row = [name, layout_info.mri, layout_info.x, layout_info.y,
                   layout_info.visible]
            layout_table.append(row)
        self.layout.set_value(layout_table)

    def do_reset(self):
        super(ManagerController, self).do_reset()
        self.set_layout(Table(self.layout.meta))

    @method_writeable_in(sm.EDITABLE)
    def edit(self):
        self.try_stateful_function(sm.EDITING, sm.EDITABLE, self.do_edit)

    def do_edit(self):
        self.revert_structure = self._save_to_structure()

    @method_writeable_in(sm.EDITABLE)
    @method_takes(
        "layoutName", StringMeta(
            "Name of layout to save to, if different from current layoutName"),
        None)
    def save(self, params):
        self.try_stateful_function(
            sm.SAVING, self.stateMachine.AFTER_RESETTING, self.do_save,
            params.layoutName)

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
        self.try_stateful_function(
            sm.REVERTING, self.stateMachine.AFTER_RESETTING, self.do_revert)

    def do_revert(self):
        self._load_from_structure(self.revert_structure)

    def load_layout(self, value):
        # TODO: Look for value in our save file location
        filename = "/tmp/" + value + ".json"
        structure = json.loads(filename)
        self._load_from_structure(structure)
        self.layout_name.set_value(value)

    def _save_to_structure(self):
        structure = self.run_hook(self.Save, self.create_part_tasks())
        structure["layout"] = self.layout.value.to_dict()
        return structure

    def _load_from_structure(self, structure):
        self.set_layout(structure["layout"])
        self.run_hook(self.Load, self.create_part_tasks(), structure)

