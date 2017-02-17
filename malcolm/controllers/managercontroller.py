import os

from malcolm.compat import OrderedDict
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import ManagerStateMachine, method_writeable_in, \
    method_takes, Hook, Table, Info, json_encode, json_decode, \
    method_also_takes, REQUIRED
from malcolm.tags import port_types
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, \
    BooleanArrayMeta, TableMeta, StringMeta, ChoiceMeta, ChoiceArrayMeta


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


class PortInfo(Info):
    """Info about an outport and its value in a class

    Args:
        direction (str): Direction of the port e.g. "in" or "out"
        type (str): Type of the port, e.g. "bool" or "NDArray"
        value (str): The current value
        extra (str): For outports, value that will be set when port is selected,
            e.g. "PCOMP1.OUT" or "DET.STATS". For inports, value that will be
            set when port is disconnected, e.g. "" or "ZERO"
    """
    def __init__(self, direction, type, value, extra):
        assert direction in ("in", "out"), \
            "Direction should be 'in' or 'out', got %r" % direction
        self.direction = direction
        assert type in port_types, \
            "Type should be in %s, got %r" % (port_types, type)
        self.type = type
        self.value = value
        self.extra = extra


class ExportableInfo(Info):
    """Info about an exportable field name and object

    Args:
        name (str): Field name, e.g. "completedSteps"
        value (object): Object, e.g. Attribute() or Method()
        setter (function): The setter for an Attribute, or post function for
            a method
    """
    def __init__(self, name, value, setter):
        self.name = name
        self.value = value
        self.setter = setter


sm = ManagerStateMachine


@method_also_takes(
    "configDir", StringMeta("Directory to write save/load config to"), REQUIRED,
    "defaultConfig", StringMeta("Default config to load"), "",
)
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # The stateMachine that this controller implements
    stateMachine = sm()

    ReportExportable = Hook()
    """Called to work out what field names the export table can contain and
    to get the actual attribute or method that it points to

    Args:
        task (Task): The task used to perform operations on child blocks

    Returns:
        [`ExportableInfo`] - the type and value of each outport of the child
    """

    ReportPorts = Hook()
    """Called before Layout to get in and out port info from children

    Args:
        task (Task): The task used to perform operations on child blocks

    Returns:
        [`PortInfo`] - the direction, type and value of each in or out port of
            the child
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
    exports = None

    # {part_name: part_structure} of currently loaded settings
    load_structure = None

    def create_attributes(self):
        for data in super(ManagerController, self).create_attributes():
            yield data
        assert os.path.isdir(self.params.configDir), \
            "%s is not a directory" % self.params.configDir
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
        # Make a choice attribute for loading an existing layout
        self.layout_name = ChoiceMeta(
            "Saved layout name to load").make_attribute()
        self.layout_name.meta.set_writeable_in(
            self.stateMachine.AFTER_RESETTING)
        yield "layoutName", self.layout_name, self.load_layout
        # Make a table for the exported fields
        columns = OrderedDict()
        columns["name"] = ChoiceArrayMeta("Name of exported block.field")
        columns["exportName"] = StringArrayMeta(
            "Name of the field within current block")
        exports_table_meta = TableMeta("Exported fields of child blocks",
                                       columns=columns)
        exports_table_meta.set_writeable_in(sm.EDITABLE)
        self.exports = exports_table_meta.make_attribute()
        yield "exports", self.exports, self.exports.set_value

    def set_layout(self, value):
        # If it isn't a table, make it one
        if not isinstance(value, Table):
            value = Table(self.layout.meta, value)
        port_part_info = PortInfo.filter_parts(self.run_hook(
            self.ReportPorts, self.create_part_tasks(only_visible=False)))
        part_info = self.run_hook(
            self.Layout, self.create_part_tasks(only_visible=False),
            port_part_info, value)
        layout_table = Table(self.layout.meta)
        for name, layout_infos in LayoutInfo.filter_parts(part_info).items():
            assert len(layout_infos) == 1, \
                "%s returned more than 1 layout infos" % name
            layout_info = layout_infos[0]
            row = [name, layout_info.mri, layout_info.x, layout_info.y,
                   layout_info.visible]
            layout_table.append(row)
        self.layout.set_value(layout_table)

    def create_part_fields(self):
        # Find the invisible parts
        invisible = []
        for name, visible in zip(
                self.layout.value.name, self.layout.value.visible):
            if not visible:
                invisible.append(name)
        # Find the exportable fields for each part
        part_info = self.run_hook(
            self.ReportExportable, self.create_part_tasks(only_visible=False))
        # {part_name: [ExportableInfo()]
        exportable = ExportableInfo.filter_parts(part_info)
        # {part_name: [(field_name, export_name)]}
        exported = {}
        for name, export_name in zip(
                self.exports.value.name, self.exports.value.exportName):
            part_name, field_name = name.rsplit(".", 1)
            if export_name == "":
                export_name = field_name
            exported.setdefault(part_name, []).append((field_name, export_name))
        # Add fields from parts that aren't invisible
        for part_name, part in self.parts.items():
            if part_name in invisible:
                continue
            for data in part.create_attributes():
                yield data
            for data in part.create_methods():
                yield data
            # Add fields in the export table
            for field_name, export_name in exported.get(part_name, []):
                for exportable_info in exportable.get(part_name, []):
                    if field_name == exportable_info.name:
                        yield export_name, exportable_info.value, \
                              exportable_info.setter

    def create_part_tasks(self, only_visible=True):
        part_tasks = super(ManagerController, self).create_part_tasks()
        if only_visible:
            for part_name, visible in zip(
                    self.layout.value.name, self.layout.value.visible):
                if not visible:
                    part_tasks.pop(self.parts[part_name])
        return part_tasks

    def do_reset(self):
        super(ManagerController, self).do_reset()
        # This will trigger all parts to report their layout, making sure the
        # layout table has a valid value
        self.set_layout(Table(self.layout.meta))
        # List the configDir and add to choices
        self._set_layout_names()
        # List the fields of every part
        self._set_exports_fields()
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
        self._set_block_children()

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

    def _set_exports_fields(self):
        # Find the exportable fields for each part
        part_info = self.run_hook(
            self.ReportExportable, self.create_part_tasks(only_visible=False))
        names = []
        # {part_name: [ExportableInfo()]
        exportable = ExportableInfo.filter_parts(part_info)
        for part_name, part_exportables in exportable.items():
            for part_exportable in part_exportables:
                names.append("%s.%s" % (part_name, part_exportable.name))
        self.exports.meta.elements.name.set_choices(sorted(names))

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
        # Add the layout table
        structure["layout"] = OrderedDict()
        for name, x, y, visible in sorted(
                zip(self.layout.value.name, self.layout.value.x,
                    self.layout.value.y, self.layout.value.visible)):
            layout_structure = OrderedDict()
            layout_structure["x"] = x
            layout_structure["y"] = y
            layout_structure["visible"] = visible
            structure["layout"][name] = layout_structure
        # Add the exports table
        structure["exports"] = OrderedDict()
        for name, export_name in sorted(
                zip(self.exports.value.name, self.exports.value.exportName)):
            structure["exports"][name] = export_name
        # Add any structure that a child part wants to save
        for part_name, part_structure in sorted(self.run_hook(
                self.Save, self.create_part_tasks(only_visible=False)).items()):
            structure[part_name] = part_structure
        return structure

    def _load_from_structure(self, structure):
        # Set the layout table
        layout_table = Table(self.layout.meta)
        for part_name, part_structure in structure.get("layout", {}).items():
            layout_table.append([
                part_name, "", part_structure["x"], part_structure["y"],
                part_structure["visible"]])
        self.set_layout(layout_table)
        # Set the exports table
        exports_table = Table(self.exports.meta)
        for name, export_name in structure.get("exports", {}).items():
            exports_table.append([name, export_name])
        self.exports.set_value(exports_table)
        # Run the load hook to get parts to load their own structure
        self.run_hook(self.Load, self.create_part_tasks(only_visible=False),
                      structure)
        self._set_block_children()
