import os

from malcolm.compat import OrderedDict
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import ManagerStateMachine, method_writeable_in, \
    method_takes, Hook, Table, Info, json_encode, json_decode, \
    method_also_takes, REQUIRED
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, \
    BooleanArrayMeta, TableMeta, StringMeta, ChoiceMeta


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


class OutportInfo(Info):
    """Info about an outport and its value in a class

    Args:
        type (str): Type of the port, e.g. bool or NDArray
        value (str): Value that will be set when port is selected, e.g.
            PCOMP1.OUT or DET.STATS
    """
    def __init__(self, type, value):
        self.type = type
        self.value = value


sm = ManagerStateMachine


@method_also_takes(
    "configDir", StringMeta("Directory to write save/load config to"), REQUIRED,
    "defaultConfig", StringMeta("Default config to load"), "",
)
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # The stateMachine that this controller implements
    stateMachine = sm()

    ReportOutports = Hook()
    """Called before Layout to get outport info from children

    Args:
        task (Task): The task used to perform operations on child blocks

    Returns:
        [`OutportInfo`] - the type and value of each outport of the child
    """

    Layout = Hook()
    """Called when layout table set and at init to update child layout

    Args:
        task (Task): The task used to perform operations on child blocks
        part_info (dict): {part_name: [Info]} returned from Layout hook
        layout_table (Table): A possibly partial set of changes to the layout
            table that should be acted on

    Returns:
        [`LayoutInfo`] - the child layout resulting from this change
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

    Returns:
        dict: serialized version of the child that could be loaded from
    """

    # attributes
    layout = None
    layout_name = None

    # {part_name: part_structure} of currently loaded settings
    load_structure = None

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
        self.layout_name = ChoiceMeta(
            "Saved layout name to load", []).make_attribute()
        self.layout_name.meta.set_writeable_in(
            self.stateMachine.AFTER_RESETTING)
        yield "layoutName", self.layout_name, self.load_layout
        assert os.path.isdir(self.params.configDir), \
            "%s is not a directory" % self.params.configDir

    def set_layout(self, value):
        # If it isn't a table, make it one
        if not isinstance(value, Table):
            value = Table(self.layout.meta, value)
        part_info = self.run_hook(self.ReportOutports, self.create_part_tasks())
        part_info = self.run_hook(
            self.Layout, self.create_part_tasks(), part_info, value)
        layout_table = Table(self.layout.meta)
        for name, layout_infos in LayoutInfo.filter_parts(part_info).items():
            assert len(layout_infos) == 1, \
                "%s returned more than 1 layout infos" % name
            layout_info = layout_infos[0]
            row = [name, layout_info.mri, layout_info.x, layout_info.y,
                   layout_info.visible]
            layout_table.append(row)
        self.layout.set_value(layout_table)

    def do_reset(self):
        super(ManagerController, self).do_reset()
        # This will trigger all parts to report their layout, making sure the
        # layout table has a valid value
        self.set_layout(Table(self.layout.meta))
        # List the configDir and add to choices
        self._set_layout_names()
        # If we have no load_structure (initial reset) define one
        if self.load_structure is None:
            if self.params.defaultConfig:
                self.load_layout(self.params.defaultConfig)
            else:
                self.load_structure = self._save_to_structure()

    @method_writeable_in(sm.READY)
    def edit(self):
        self.transition(sm.EDITABLE, "Layout editable")

    def go_to_error_state(self, exception):
        if self.state.value == sm.EDITABLE:
            # If we got a save or revert exception, don't go to fault
            self.log_exception("Fault occurred while trying to save/revert")
        else:
            super(ManagerController, self).go_to_error_state(exception)

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
        if not layout_name:
            layout_name = self.layout_name.value
        structure = self._save_to_structure()
        text = json_encode(structure, indent=2)
        filename = self._validated_config_filename(layout_name)
        open(filename, "w").write(text)
        self._set_layout_names(layout_name)
        self.layout_name.set_value(layout_name)
        self.load_structure = structure

    def _set_layout_names(self, extra_name=None):
        names = []
        if extra_name:
            names.append(extra_name)
        dir_name = self._make_config_dir()
        for f in os.listdir(dir_name):
            if os.path.isfile(
                    os.path.join(dir_name, f)) and f.endswith(".json"):
                names.append(f.split(".json")[0])
        self.layout_name.meta.set_choices(names)

    @method_writeable_in(sm.EDITABLE)
    def revert(self):
        self.try_stateful_function(
            sm.REVERTING, self.stateMachine.AFTER_RESETTING, self.do_revert)

    def do_revert(self):
        self._load_from_structure(self.load_structure)

    def _validated_config_filename(self, name):
        """Make config dir and return full file path and extension

        Args:
            name (str): Filename without dir or extension

        Returns:
            str: Full path including extensio
        """
        dir_name = self._make_config_dir()
        filename = os.path.join(dir_name, name.split(".json")[0] + ".json")
        return filename

    def _make_config_dir(self):
        dir_name = os.path.join(self.params.configDir, self.mri)
        try:
            os.mkdir(dir_name)
        except OSError:
            # OK if already exists, if not then it will fail on write anyway
            pass
        return dir_name

    def load_layout(self, value):
        # TODO: race condition if we get 2 loads at once...
        # Do we need a Loading state?
        filename = self._validated_config_filename(value)
        text = open(filename, "r").read()
        structure = json_decode(text)
        self._load_from_structure(structure)
        self.layout_name.set_value(value)

    def _save_to_structure(self):
        structure = OrderedDict()
        structure["layout"] = OrderedDict()
        for name, x, y, visible in sorted(
                zip(self.layout.value.name, self.layout.value.x,
                    self.layout.value.y, self.layout.value.visible)):
            layout_structure = OrderedDict()
            layout_structure["x"] = x
            layout_structure["y"] = y
            layout_structure["visible"] = visible
            structure["layout"][name] = layout_structure
        for part_name, part_structure in sorted(self.run_hook(
                self.Save, self.create_part_tasks()).items()):
            structure[part_name] = part_structure
        return structure

    def _load_from_structure(self, structure):
        table = Table(self.layout.meta)
        for part_name, part_structure in structure["layout"].items():
            table.append([part_name, "", part_structure["x"],
                          part_structure["y"], part_structure["visible"]])
        self.set_layout(table)
        self.run_hook(self.Load, self.create_part_tasks(), structure)

