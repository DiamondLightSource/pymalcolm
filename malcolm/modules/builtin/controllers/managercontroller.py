import os
import subprocess

import numpy as np

from malcolm.compat import OrderedDict
from malcolm.core import method_writeable_in, method_takes, Hook, Table, \
    json_encode, json_decode, method_also_takes, REQUIRED, Unsubscribe, \
    Subscribe, deserialize_object, Delta, Context, AttributeModel, Alarm, \
    AlarmSeverity, AlarmStatus
from malcolm.modules.builtin.infos import LayoutInfo
from malcolm.modules.builtin.vmetas import StringArrayMeta, NumberArrayMeta, \
    BooleanArrayMeta, TableMeta, StringMeta, ChoiceMeta, ChoiceArrayMeta, \
    BooleanMeta
from malcolm.tags import widget, config
from .statefulcontroller import StatefulController, StatefulStates


class ManagerStates(StatefulStates):
    SAVING = "Saving"
    LOADING = "Loading"

    def create_block_transitions(self):
        super(ManagerStates, self).create_block_transitions()
        self.set_allowed(self.READY, self.SAVING)
        self.set_allowed(self.SAVING, self.READY)
        self.set_allowed(self.READY, self.LOADING)
        self.set_allowed(self.LOADING, self.READY)


ss = ManagerStates


@method_also_takes(
    "configDir", StringMeta("Directory to write save/load config to"), REQUIRED,
    "initialDesign", StringMeta("Design to load at init"), "",
)
class ManagerController(StatefulController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    stateSet = ss()

    Layout = Hook()
    """Called when layout table set and at init to update child layout

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        part_info (dict): {part_name: [Info]} returned from Layout hook
        layout_table (Table): A possibly partial set of changes to the layout
            table that should be acted on

    Returns:
        [`LayoutInfo`] - the child layout resulting from this change
    """

    Load = Hook()
    """Called at load() or revert() to load child settings from a structure

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        structure (dict): {part_name: part_structure} where part_structure is
            the return from Save hook
    """

    Save = Hook()
    """Called at save() to serialize child settings into a dict structure

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks

    Returns:
        dict: serialized version of the child that could be loaded from
    """

    # Attributes
    layout = None
    design = None
    exports = None
    modified = None

    def __init__(self, process, parts, params):
        super(ManagerController, self).__init__(process, parts, params)
        # last saved layout and exports
        self.saved_visibility = None
        self.saved_exports = None
        # ((name, AttributeModel/MethodModel, setter))
        self._current_part_fields = ()
        # [Subscribe]
        self._subscriptions = []
        # {part_name: [PortInfo]}
        self.port_info = {}
        # {part: [attr_name]}
        self.part_exportable = {}
        # {part: Alarm}
        self.part_modified = {}
        # Whether to do updates
        self._do_update = True

    def _run_git_cmd(self, *args):
        # Run git command, don't care if it fails, logging the output
        try:
            output = subprocess.check_output(
                ("git",) + args, cwd=self.params.configDir)
        except subprocess.CalledProcessError as e:
            self.log.warning("Git command failed: %s\n%s", e, e.output)
        else:
            self.log.debug("Git command completed: %s", output)

    def create_attribute_models(self):
        for data in super(ManagerController, self).create_attribute_models():
            yield data
        assert os.path.isdir(self.params.configDir), \
            "%s is not a directory" % self.params.configDir
        if not os.path.isdir(os.path.join(self.params.configDir, ".git")):
            # Try and make it a git repo, don't care if it fails
            self._run_git_cmd("init")
            self._run_git_cmd("commit", "--allow-empty", "-m", "Created repo")
        # Create writeable attribute table for the layout info we need
        elements = OrderedDict()
        elements["name"] = StringArrayMeta("Name of layout part")
        elements["mri"] = StringArrayMeta("Malcolm full name of child block")
        elements["x"] = NumberArrayMeta(
            "float64", "X Coordinate of child block")
        elements["y"] = NumberArrayMeta(
            "float64", "Y Coordinate of child block")
        elements["visible"] = BooleanArrayMeta("Whether child block is visible")
        layout_table_meta = TableMeta(
            "Layout of child blocks", elements=elements,
            tags=[widget("flowgraph")])
        layout_table_meta.set_writeable_in(ss.READY)
        self.layout = layout_table_meta.create_attribute_model()
        yield "layout", self.layout, self.set_layout
        # Create writeable attribute for loading an existing layout
        design_meta = ChoiceMeta(
            "Design name to load", tags=[config(), widget("combo")])
        design_meta.set_writeable_in(ss.READY)
        self.design = design_meta.create_attribute_model()
        yield "design", self.design, self.set_design
        # Create writeable attribute table for the exported fields
        elements = OrderedDict()
        elements["name"] = ChoiceArrayMeta("Name of exported block.field")
        elements["exportName"] = StringArrayMeta(
            "Name of the field within current block")
        exports_table_meta = TableMeta(
            "Exported fields of child blocks", tags=[widget("table")],
            elements=elements)
        exports_table_meta.set_writeable_in(ss.READY)
        self.exports = exports_table_meta.create_attribute_model()
        yield "exports", self.exports, self.set_exports
        # Create read-only indicator for when things are modified
        modified_meta = BooleanMeta(
            "Whether the design is modified", tags=[widget("led")])
        self.modified = modified_meta.create_attribute_model()
        yield "modified", self.modified, None

    def do_init(self):
        # This will do an initial poll of the exportable parts,
        # so don't update here
        super(ManagerController, self).do_init()
        # List the configDir and add to choices
        self._set_layout_names()
        # This will trigger all parts to report their layout, making sure
        # the layout table has a valid value. This will also call
        # self._update_block_endpoints()
        self.set_layout(Table(self.layout.meta))
        # If given a default config, load this
        if self.params.initialDesign:
            self.do_load(self.params.initialDesign)

    def set_layout(self, value):
        """Set the layout table value. Called on attribute put"""
        # If it isn't a table, make it one
        if not isinstance(value, Table):
            value = Table(self.layout.meta, value)
        # Can't do this with changes_squashed as it will call update_modified
        # from another thread and deadlock
        part_info = self.run_hook(
            self.Layout, self.create_part_contexts(only_visible=False),
            self.port_info, value)
        with self.changes_squashed:
            layout_table = Table(self.layout.meta)
            layout_parts = LayoutInfo.filter_parts(part_info)
            for name, layout_infos in layout_parts.items():
                assert len(layout_infos) == 1, \
                    "%s returned more than 1 layout infos" % name
                layout_parts[name] = layout_infos[0]
            layout_table.name = list(layout_parts)
            layout_table.mri = [i.mri for i in layout_parts.values()]
            layout_table.x = [i.x for i in layout_parts.values()]
            layout_table.y = [i.y for i in layout_parts.values()]
            layout_table.visible = [i.visible for i in layout_parts.values()]
            try:
                np.testing.assert_equal(
                    layout_table.visible, self.layout.value.visible)
            except AssertionError:
                visibility_changed = True
            else:
                visibility_changed = False
            self.layout.set_value(layout_table)
            if self.saved_visibility is None:
                # First write of table, set layout and exports saves
                self.saved_visibility = layout_table.visible
                self.saved_exports = self.exports.value.to_dict()
            if visibility_changed:
                self.update_modified()
                self.update_exportable()
                # Part visibility changed, might have attributes or methods
                # that we need to hide or show
                self._update_block_endpoints()

    def set_exports(self, value):
        with self.changes_squashed:
            self.exports.set_value(value)
            self.update_modified()
            self._update_block_endpoints()

    def update_modified(self, part=None, alarm=None):
        with self.changes_squashed:
            # Update the alarm for the given part
            if part:
                self.part_modified[part] = alarm
            # Find the modified alarms for each visible part
            message_list = []
            only_modified_by_us = True
            for part_name, visible in zip(
                    self.layout.value.name, self.layout.value.visible):
                if visible:
                    alarm = self.part_modified.get(self.parts[part_name], None)
                    if alarm:
                        # Part flagged as been modified, is it by us?
                        if alarm.severity:
                            only_modified_by_us = False
                        message_list.append(alarm.message)
            # Add in any modification messages from the layout and export tables
            try:
                np.testing.assert_equal(
                    self.layout.value.visible, self.saved_visibility)
            except AssertionError:
                message_list.append("layout changed")
                only_modified_by_us = False
            try:
                np.testing.assert_equal(
                    self.exports.value.to_dict(), self.saved_exports)
            except AssertionError:
                message_list.append("exports changed")
                only_modified_by_us = False
            if message_list:
                if only_modified_by_us:
                    severity = AlarmSeverity.NO_ALARM
                else:
                    severity = AlarmSeverity.MINOR_ALARM
                alarm = Alarm(
                    severity, AlarmStatus.CONF_STATUS, "\n".join(message_list))
                self.modified.set_value(True, alarm=alarm)
            else:
                self.modified.set_value(False)

    def update_exportable(self, part=None, fields=None, port_infos=None):
        with self.changes_squashed:
            if part:
                self.part_exportable[part] = fields
                self.port_info[part.name] = port_infos
            # Find the exportable fields for each visible part
            names = []
            for part in self.parts.values():
                fields = self.part_exportable.get(part, [])
                for attr_name in fields:
                    names.append("%s.%s" % (part.name, attr_name))
            changed_names = set(names).symmetric_difference(
                self.exports.meta.elements["name"].choices)
            changed_exports = changed_names.intersection(
                self.exports.value.name)
            self.exports.meta.elements["name"].set_choices(names)
            # Update the block endpoints if anything currently exported is
            # added or deleted
            if changed_exports:
                self._update_block_endpoints()

    def _update_block_endpoints(self):
        if self._current_part_fields:
            for name, child, _ in self._current_part_fields:
                self._block.remove_endpoint(name)
                for state, state_writeable in self._children_writeable.items():
                    state_writeable.pop(child, None)
        self._current_part_fields = tuple(self._get_current_part_fields())
        for name, child, writeable_func in self._current_part_fields:
            self.add_block_field(name, child, writeable_func)

    def initial_part_fields(self):
        # Don't return any fields to start with, these will be added on load()
        return iter(())

    def _get_current_part_fields(self):
        # Clear out the current subscriptions
        for subscription in self._subscriptions:
            controller = self.process.get_controller(subscription.path[0])
            unsubscribe = Unsubscribe(subscription.id, subscription.callback)
            controller.handle_request(unsubscribe)
        self._subscriptions = []

        # Find the mris of parts
        mris = {}
        invisible = set()
        for part_name, mri, visible in zip(
                self.layout.value.name,
                self.layout.value.mri,
                self.layout.value.visible):
            if visible:
                mris[part_name] = mri
            else:
                invisible.add(part_name)

        # Add fields from parts that aren't invisible
        for part_name in self.parts:
            if part_name not in invisible:
                for data in self.part_fields[part_name]:
                    yield data

        # Add exported fields from visible parts
        for name, export_name in zip(
                self.exports.value.name, self.exports.value.exportName):
            part_name, attr_name = name.rsplit(".", 1)
            part = self.parts[part_name]
            # If part is visible, get its mri
            mri = mris.get(part_name, None)
            if mri and attr_name in self.part_exportable.get(part, []):
                if not export_name:
                    export_name = attr_name
                export, setter = self._make_export_field(mri, attr_name)
                yield export_name, export, setter

    def _make_export_field(self, mri, attr_name):
        controller = self.process.get_controller(mri)
        path = [mri, attr_name]
        ret = {}

        def update_field(response):
            if not isinstance(response, Delta):
                # Return or Error is the end of our subscription, log and ignore
                self.log.debug("Export got response %r", response)
                return
            if not ret:
                # First call, create the initial object
                ret["export"] = deserialize_object(response.changes[0][1])
                context = Context(self.process)
                if isinstance(ret["export"], AttributeModel):
                    def setter(v):
                        context.put(path, v)
                else:
                    def setter(*args):
                        context.post(path, *args)
                ret["setter"] = setter
            else:
                # Subsequent calls, update it
                with self.changes_squashed:
                    for cp, value in response.changes:
                        ob = ret["export"]
                        for p in cp[:-1]:
                            ob = ob[p]
                        getattr(ob, "set_%s" % cp[-1])(value)

        subscription = Subscribe(path=path, delta=True, callback=update_field)
        self._subscriptions.append(subscription)
        # When we have waited for the subscription, the first update_field
        # will have been called
        controller.handle_request(subscription).wait()
        return ret["export"], ret["setter"]

    def create_part_contexts(self, only_visible=True):
        part_contexts = super(ManagerController, self).create_part_contexts()
        if only_visible:
            for part_name, visible in zip(
                    self.layout.value.name, self.layout.value.visible):
                if not visible:
                    part_contexts.pop(self.parts[part_name])
        return part_contexts

    @method_writeable_in(ss.READY)
    @method_takes(
        "design", StringMeta(
            "Name of design to save, if different from current design"), "")
    def save(self, params):
        """Save the current design to file"""
        self.try_stateful_function(
            ss.SAVING, ss.READY, self.do_save, params.design)

    def do_save(self, design=""):
        if not design:
            design = self.design.value
        assert design, "Please specify save design name when saving from new"
        structure = OrderedDict()
        # Add the layout table
        part_layouts = {}
        for name, x, y, visible in sorted(
                zip(self.layout.value.name, self.layout.value.x,
                    self.layout.value.y, self.layout.value.visible)):
            layout_structure = OrderedDict()
            layout_structure["x"] = x
            layout_structure["y"] = y
            layout_structure["visible"] = visible
            part_layouts[name] = layout_structure
        structure["layout"] = OrderedDict()
        for part_name in self.parts:
            if part_name in part_layouts:
                structure["layout"][part_name] = part_layouts[part_name]
        # Add the exports table
        structure["exports"] = OrderedDict()
        for name, export_name in sorted(
                zip(self.exports.value.name, self.exports.value.exportName)):
            structure["exports"][name] = export_name
        # Add any structure that a child part wants to save
        part_structures = self.run_hook(
            self.Save, self.create_part_contexts(only_visible=False))
        for part_name, part_structure in sorted(part_structures.items()):
            structure[part_name] = part_structure
        text = json_encode(structure, indent=2)
        filename = self._validated_config_filename(design)
        with open(filename, "w") as f:
            f.write(text)
        if os.path.isdir(os.path.join(self.params.configDir, ".git")):
            # Try and commit the file to git, don't care if it fails
            self._run_git_cmd("add", filename)
            msg = "Saved %s %s" % (self.mri, design)
            self._run_git_cmd("commit", "--allow-empty", "-m", msg, filename)
        self._mark_clean(design)

    def _set_layout_names(self, extra_name=None):
        names = [""]
        if extra_name:
            names.append(extra_name)
        dir_name = self._make_config_dir()
        for f in os.listdir(dir_name):
            if os.path.isfile(
                    os.path.join(dir_name, f)) and f.endswith(".json"):
                names.append(f.split(".json")[0])
        self.design.meta.set_choices(names)

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

    def set_design(self, value):
        value = self.design.meta.validate(value)
        self.try_stateful_function(
            ss.LOADING, ss.READY, self.do_load, value)

    def do_load(self, design):
        filename = self._validated_config_filename(design)
        with open(filename, "r") as f:
            text = f.read()
        structure = json_decode(text)
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
        self.run_hook(self.Load,
                      self.create_part_contexts(only_visible=False),
                      structure)
        self._mark_clean(design)

    def _mark_clean(self, design):
        with self.changes_squashed:
            self.saved_visibility = self.layout.value.visible
            self.saved_exports = self.exports.value.to_dict()
            # Now we are clean, modified should clear
            self.part_modified = OrderedDict()
            self.update_modified()
            self._set_layout_names(design)
            self.design.set_value(design)
            self._update_block_endpoints()
