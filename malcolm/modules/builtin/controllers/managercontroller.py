import os
import subprocess

import numpy as np
from annotypes import Anno, add_call_types, TYPE_CHECKING

from malcolm.compat import OrderedDict
from malcolm.core import json_encode, json_decode, Unsubscribe, Subscribe, \
    deserialize_object, Delta, Context, AttributeModel, Alarm, AlarmSeverity, \
    AlarmStatus, Part, BooleanMeta, config_tag, Widget, ChoiceMeta, \
    TableMeta, serialize_object
from malcolm.modules.builtin.infos import PortInfo
from malcolm.modules.builtin.util import ManagerStates
from ..hooks import LayoutHook, LoadHook, SaveHook
from ..infos import LayoutInfo, PartExportableInfo, PartModifiedInfo
from ..util import LayoutTable, ExportTable
from .statefulcontroller import StatefulController, AMri, \
    ADescription, AUseCothread

if TYPE_CHECKING:
    from typing import Dict, List

ss = ManagerStates


with Anno("Directory to write save/load config to"):
    AConfigDir = str
with Anno("Design to load at init"):
    AInitialDesign = str
with Anno("Use git to manage to saved config files"):
    AUseGit = bool
with Anno("Name of design to save, if different from current design"):
    ASaveDesign = str


class ManagerController(StatefulController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    state_set = ss()

    def __init__(self,
                 mri,  # type: AMri
                 config_dir,  # type: AConfigDir
                 initial_design="",  # type: AInitialDesign
                 description="",  # type: ADescription
                 use_cothread=True,  # type: AUseCothread
                 use_git=True,  # type: AUseGit
                 ):
        # type: (...) -> None
        super(ManagerController, self).__init__(mri, description, use_cothread)
        assert os.path.isdir(config_dir), "%s is not a directory" % config_dir
        self.config_dir = config_dir
        self.initial_design = initial_design
        self.use_git = use_git
        # last saved layout and exports
        self.saved_visibility = None
        self.saved_exports = None
        # ((name, AttributeModel/MethodModel, setter))
        self._current_part_fields = ()
        # [Subscribe]
        self._subscriptions = []
        # {part_name: [PortInfo]}
        self.port_info = {}  # type: Dict[str, List[PortInfo]]
        # {part: [attr_name]}
        self.part_exportable = {}
        # {part: Alarm}
        self.part_modified = {}
        # The attributes our part has published
        self.our_config_attributes = {}  # type: Dict[str, AttributeModel]]
        # Whether to do updates
        self._do_update = True
        # The reportable infos we are listening for
        self.info_registry.add_reportable(
            PartModifiedInfo, self.update_modified)
        # Update queue of exportable fields
        self.info_registry.add_reportable(
            PartExportableInfo, self.update_exportable)
        # Create a layout table attribute for setting block positions
        self.layout = TableMeta.from_table(
            LayoutTable, "Layout of child blocks", Widget.FLOWGRAPH
        ).create_attribute_model()
        self.set_writeable_in(self.layout, ss.READY)
        self.field_registry.add_attribute_model(
            "layout", self.layout, self.set_layout)
        # Create a design attribute for loading an existing layout
        self.design = ChoiceMeta(
            "Design name to load", tags=[config_tag(), Widget.COMBO.tag()]
        ).create_attribute_model()
        self.field_registry.add_attribute_model(
            "design", self.design, self.set_design)
        self.set_writeable_in(self.design, ss.READY)
        # Create an export table for mirroring exported fields
        self.exports = TableMeta.from_table(
            ExportTable, "Exported fields of child blocks"
        ).create_attribute_model()
        # Overwrite the sources meta to be a ChoiceMeta
        self.exports.meta.elements["source"] = ChoiceMeta(
            "Name of the block.field to export", tags=[Widget.COMBO.tag()])
        self.set_writeable_in(self.exports, ss.READY)
        self.field_registry.add_attribute_model(
            "exports", self.exports, self.set_exports)
        # Create read-only indicator for when things are modified
        self.modified = BooleanMeta(
            "Whether the design is modified", tags=[Widget.LED.tag()]
        ).create_attribute_model()
        self.field_registry.add_attribute_model("modified", self.modified)
        # Create the save method
        self.set_writeable_in(
            self.field_registry.add_method_model(self.save), ss.READY)

    def _run_git_cmd(self, *args):
        # Run git command, don't care if it fails, logging the output
        if self.use_git and os.path.isdir(
                os.path.join(self.config_dir, ".git")):
            try:
                output = subprocess.check_output(
                    ("git",) + args, cwd=self.config_dir)
            except subprocess.CalledProcessError as e:
                self.log.warning("Git command failed: %s\n%s", e, e.output)
            else:
                self.log.debug("Git command completed: %s", output)

    def do_init(self):
        super(ManagerController, self).do_init()
        # Try and make it a git repo, don't care if it fails
        self._run_git_cmd("init")
        self._run_git_cmd("commit", "--allow-empty", "-m", "Created repo")
        # List the config_dir and add to choices
        self._set_layout_names()
        # If given a default config, load this
        if self.initial_design:
            self.do_load(self.initial_design)
        else:
            # This will trigger all parts to report their layout, making sure
            # the layout table has a valid value. This will also call
            # self._update_block_endpoints()
            self.set_layout(LayoutTable([], [], [], [], []))

    def set_layout(self, value):
        """Set the layout table value. Called on attribute put"""
        # Can't do this with changes_squashed as it will call update_modified
        # from another thread and deadlock. Need RLock.is_owned() from update_*
        part_info = self.run_hooks(
            LayoutHook(p, c, self.port_info, value)
            for p, c in self.create_part_contexts(only_visible=False).items())
        with self.changes_squashed:
            layout_parts = LayoutInfo.filter_parts(part_info)
            name, mri, x, y, visible = [], [], [], [], []
            for part_name, layout_infos in layout_parts.items():
                for layout_info in layout_infos:
                    name.append(part_name)
                    mri.append(layout_info.mri)
                    x.append(layout_info.x)
                    y.append(layout_info.y)
                    visible.append(layout_info.visible)
            layout_table = LayoutTable(name, mri, x, y, visible)
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
                self.update_block_endpoints()

    def set_exports(self, value):
        with self.changes_squashed:
            self.exports.set_value(value)
            self.update_modified()
            self.update_block_endpoints()

    def update_modified(self, part=None, info=None):
        # type: (Part, PartModifiedInfo) -> None
        with self.changes_squashed:
            if part:
                # Update the alarm for the given part
                self.part_modified[part] = info.alarm
            # Find the modified alarms for each visible part
            message_list = []
            only_modified_by_us = True
            for part_name, visible in zip(
                    self.layout.value.name, self.layout.value.visible):
                if visible:
                    alarm = self.part_modified.get(self.parts[part_name], None)
                    if alarm:
                        # Part flagged as been modified, is it by us?
                        if alarm.severity != AlarmSeverity.NO_ALARM:
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

    def update_exportable(self, part=None, info=None):
        # type: (Part, PartExportableInfo) -> None
        with self.changes_squashed:
            if part:
                self.part_exportable[part] = info.names
                self.port_info[part.name] = info.port_infos
            # Find the exportable fields for each visible part
            names = []
            for part in self.parts.values():
                fields = self.part_exportable.get(part, [])
                for attr_name in fields:
                    names.append("%s.%s" % (part.name, attr_name))
            changed_names = set(names).symmetric_difference(
                self.exports.meta.elements["source"].choices)
            changed_exports = changed_names.intersection(
                self.exports.value.source)
            self.exports.meta.elements["source"].set_choices(names)
            # Update the block endpoints if anything currently exported is
            # added or deleted
            if changed_exports:
                self.update_block_endpoints()

    def update_block_endpoints(self):
        if self._current_part_fields:
            for name, child, _ in self._current_part_fields:
                self._block.remove_endpoint(name)
                for state, state_writeable in self._children_writeable.items():
                    state_writeable.pop(child, None)
        self._current_part_fields = tuple(self._get_current_part_fields())
        for name, child, writeable_func in self._current_part_fields:
            self.add_block_field(name, child, writeable_func)

    def add_initial_part_fields(self):
        # Only add our own fields to start with, the rest will be added on load
        for name, child, writeable_func in self.field_registry.fields[None]:
            self.add_block_field(name, child, writeable_func)
        for part in self.parts.values():
            for name, field, writeable_func in self.field_registry.fields.get(
                    part, []):
                if isinstance(field, AttributeModel) and \
                        config_tag() in field.meta.tags:
                    # Strip off the "config" tags from attributes
                    assert writeable_func == field.set_value, \
                        "Can't save %s with writeable_func %s" % (
                            name, writeable_func)
                    field.meta.set_tags(
                        [x for x in field.meta.tags if x != config_tag()])
                    self.our_config_attributes[name] = field

    def _get_current_part_fields(self):
        # Clear out the current subscriptions
        for subscription in self._subscriptions:
            controller = self.process.get_controller(subscription.path[0])
            unsubscribe = Unsubscribe(subscription.id)
            unsubscribe.set_callback(subscription.callback)
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
        for part_name, part in self.parts.items():
            if part_name not in invisible:
                for data in self.field_registry.fields.get(part, []):
                    yield data

        # Add exported fields from visible parts
        for source, export_name in self.exports.value.rows():
            part_name, attr_name = source.rsplit(".", 1)
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

        subscription = Subscribe(path=path, delta=True)
        subscription.set_callback(update_field)
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

    @add_call_types
    def save(self, design=""):
        # type: (ASaveDesign) -> None
        """Save the current design to file"""
        self.try_stateful_function(ss.SAVING, ss.READY, self.do_save, design)

    def do_save(self, design=""):
        if not design:
            design = self.design.value
        assert design, "Please specify save design name when saving from new"
        structure = OrderedDict()
        attributes = structure.setdefault("attributes", OrderedDict())
        # Add the layout table
        layout = attributes.setdefault("layout", OrderedDict())
        for name, mri, x, y, visible in self.layout.value.rows():
            layout_structure = OrderedDict()
            layout_structure["x"] = x
            layout_structure["y"] = y
            layout_structure["visible"] = visible
            layout[name] = layout_structure
        # Add the exports table
        exports = attributes.setdefault("exports", OrderedDict())
        for source, export in self.exports.value.rows():
            exports[source] = export
        # Add other attributes
        for name, attribute in self.our_config_attributes.items():
            attributes[name] = serialize_object(attribute.value)
        # Add any structure that a child part wants to save
        structure["children"] = self.run_hooks(
            SaveHook(p, c)
            for p, c in self.create_part_contexts(only_visible=False).items())
        text = json_encode(structure, indent=2)
        filename = self._validated_config_filename(design)
        with open(filename, "w") as f:
            f.write(text)
        # Try and commit the file to git, don't care if it fails
        self._run_git_cmd("add", filename)
        msg = "Saved %s %s" % (self.mri, design)
        self._run_git_cmd("commit", "--allow-empty", "-m", msg, filename)
        self._mark_clean(design)

    def _set_layout_names(self, extra_name=None):
        names = [""]
        dir_name = self._make_config_dir()
        for f in os.listdir(dir_name):
            if os.path.isfile(
                    os.path.join(dir_name, f)) and f.endswith(".json"):
                names.append(f.split(".json")[0])
        if extra_name and str(extra_name) not in names:
            names.append(str(extra_name))
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
        dir_name = os.path.join(self.config_dir, self.mri)
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
        if design:
            filename = self._validated_config_filename(design)
            with open(filename, "r") as f:
                text = f.read()
            structure = json_decode(text)
        else:
            structure = {}
        # Attributes and Children used to be merged, support this
        attributes = structure.get("attributes", structure)
        children = structure.get("children", structure)
        # Set the layout table
        name, mri, x, y, visible = [], [], [], [], []
        for part_name, d in attributes.get("layout", {}).items():
            name.append(part_name)
            mri.append("")
            x.append(d["x"])
            y.append(d["y"])
            visible.append(d["visible"])
        self.set_layout(LayoutTable(name, mri, x, y, visible))
        # Set the exports table
        source, export = [], []
        for source_name, export_name in attributes.get("exports", {}).items():
            source.append(source_name)
            export.append(export_name)
        self.exports.set_value(ExportTable(source, export))
        # Set other attributes
        for name, attr in self.our_config_attributes.items():
            if name in attributes:
                attr.set_value(attributes[name])
        # Run the load hook to get parts to load their own structure
        self.run_hooks(
            LoadHook(p, c, children.get(p.name, {}))
            for p, c in self.create_part_contexts(only_visible=False).items())
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
            self.update_block_endpoints()
