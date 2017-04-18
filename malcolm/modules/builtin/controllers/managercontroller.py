import os

import numpy as np

from malcolm.compat import OrderedDict
from malcolm.core import method_writeable_in, method_takes, Hook, Table, \
    json_encode, json_decode, method_also_takes, REQUIRED, Unsubscribe, \
    Subscribe, deserialize_object, Delta, Context, AttributeModel, Alarm, \
    AlarmSeverity, AlarmStatus, Response
from malcolm.infos.builtin import ExportableInfo, LayoutInfo, PortInfo, \
    ModifiedInfo
from malcolm.tags import widget, config
from malcolm.modules.builtin.vmetas import StringArrayMeta, NumberArrayMeta, \
    BooleanArrayMeta, TableMeta, StringMeta, ChoiceMeta, ChoiceArrayMeta, \
    BooleanMeta
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
    "defaultConfig", StringMeta("Default config to load"), "",
)
class ManagerController(StatefulController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    stateSet = ss()

    ReportExportable = Hook()
    """Called to work out what field names the export table can contain and
    to get the actual attribute or method that it points to. A call to
    update_exportable() will cause this Hook to be run again.

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks

    Returns:
        [`ExportableInfo`] - the name of each exportable field and the child mri
    """

    ReportModified = Hook()
    """Called to work out what has been modified since the last save/load. A
    call to update_modified() will cause this Hook to be run again.

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks

    Returns:
        [`ModifiedInfo`] - the name of the field, saved and current values
    """

    ReportPorts = Hook()
    """Called before Layout to get in and out port info from children

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks

    Returns:
        [`PortInfo`] - the direction, type and value of each in or out port of
            the child
    """

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
        self.saved_layout = None
        self.saved_exports = None
        # ((name, AttributeModel/MethodModel, setter))
        self._current_part_fields = ()
        # [Subscribe]
        self._subscriptions = []

    def create_attributes(self):
        for data in super(ManagerController, self).create_attributes():
            yield data
        assert os.path.isdir(self.params.configDir), \
            "%s is not a directory" % self.params.configDir
        # Make a table for the layout info we need
        elements = OrderedDict()
        elements["name"] = StringArrayMeta("Name of layout part")
        elements["mri"] = StringArrayMeta("Malcolm full name of child block")
        elements["x"] = NumberArrayMeta(
            "float64", "X Coordinate of child block")
        elements["y"] = NumberArrayMeta(
            "float64", "Y Coordinate of child block")
        elements["visible"] = BooleanArrayMeta("Whether child block is visible")
        layout_table_meta = TableMeta(
            "Layout of child blocks", tags=[widget("table")], elements=elements)
        layout_table_meta.set_writeable_in(ss.READY)
        self.layout = layout_table_meta.create_attribute()
        yield "layout", self.layout, self.set_layout
        # Make a choice attribute for loading an existing layout
        self.design = ChoiceMeta(
            "Design name to load", tags=[config(), widget("combo")]
        ).create_attribute()
        self.design.meta.set_writeable_in(ss.READY)
        yield "design", self.design, self.set_design
        # Make a table for the exported fields
        elements = OrderedDict()
        elements["name"] = ChoiceArrayMeta("Name of exported block.field")
        elements["exportName"] = StringArrayMeta(
            "Name of the field within current block")
        exports_table_meta = TableMeta(
            "Exported fields of child blocks", tags=[widget("table")],
            elements=elements)
        exports_table_meta.set_writeable_in(ss.READY)
        self.exports = exports_table_meta.create_attribute()
        yield "exports", self.exports, self.set_exports
        # Make an indicator for when things are modified
        self.modified = BooleanMeta(
            "Whether the design is modified", tags=[widget("led")]
        ).create_attribute()
        yield "modified", self.modified, None

    def do_init(self):
        super(ManagerController, self).do_init()
        # List the configDir and add to choices
        self._set_layout_names()
        # This will trigger all parts to report their layout, making sure
        # the layout table has a valid value. It will also do
        # _update_block_endpoints()
        self.set_layout(Table(self.layout.meta))
        # If given a default config, load this
        if self.params.defaultConfig:
            self.do_load(self.params.defaultConfig)

    def set_layout(self, value, update_block=True):
        """Set the layout table value. Called on attribute put"""
        # If it isn't a table, make it one
        with self.changes_squashed:
            if not isinstance(value, Table):
                value = Table(self.layout.meta, value)
            port_part_info = PortInfo.filter_parts(self.run_hook(
                self.ReportPorts, self.create_part_contexts(
                    only_visible=False)))
            part_info = self.run_hook(
                self.Layout, self.create_part_contexts(only_visible=False),
                port_part_info, value)
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
            if not self.saved_layout:
                # First write of table, set layout and exports saves
                self.saved_layout = layout_table.to_dict()
                self.saved_exports = self.exports.value.to_dict()
            self.update_modified()
            if visibility_changed:
                self.update_exportable(update_block=False)
                if update_block:
                    # Part visibility changed, might have attributes or methods
                    # that we need to hide or show
                    self._update_block_endpoints()

    def set_exports(self, value):
        with self.changes_squashed:
            self.exports.set_value(value)
            self.update_modified()
            self._update_block_endpoints()

    def update_modified(self):
        with self.changes_squashed:
            # Find the modified fields for each visible part
            part_info = self.run_hook(
                self.ReportModified, self.create_part_contexts())
            # {part_name: [ModifiedInfo()]
            modified_infos = ModifiedInfo.filter_parts(part_info)
            message_list = []
            for part_name, infos in modified_infos.items():
                for info in infos:
                    message = "%s.%s.value = %r not %r" % (
                        part_name, info.name, info.current_value,
                        info.original_value)
                    message_list.append(message)
            # Add in any modification messages from the layout and export tables
            try:
                np.testing.assert_equal(
                    self.layout.value.to_dict(), self.saved_layout)
            except AssertionError:
                message_list.append("layout changed")
            try:
                np.testing.assert_equal(
                    self.exports.value.to_dict(), self.saved_exports)
            except AssertionError:
                message_list.append("exports changed")
            if message_list:
                alarm = Alarm(AlarmSeverity.MINOR_ALARM,
                              AlarmStatus.CONF_STATUS,
                              "\n".join(message_list))
                self.modified.set_value(True, alarm=alarm)
            else:
                self.modified.set_value(False)

    def update_exportable(self, update_block=True):
        with self.changes_squashed:
            # Find the exportable fields for each visible part
            part_info = self.run_hook(
                self.ReportExportable, self.create_part_contexts())
            names = []
            # {part_name: [ExportableInfo()]
            exportable = ExportableInfo.filter_parts(part_info)
            for part_name, part_exportables in sorted(exportable.items()):
                for part_exportable in part_exportables:
                    names.append(
                        "%s.%s" % (part_name, part_exportable.name))
            changed_names = set(names).symmetric_difference(
                self.exports.meta.elements["name"].choices)
            changed_exports = changed_names.intersection(
                self.exports.value.name)
            self.exports.meta.elements["name"].set_choices(names)
            # Update the block endpoints if anything currently exported is
            # added or deleted
            if changed_exports and update_block:
                self._update_block_endpoints()

    def _update_block_endpoints(self):
        if self._current_part_fields:
            for name, _, _ in self._current_part_fields:
                self._block.remove_endpoint(name)
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

        # Find the invisible parts
        invisible = []
        for name, visible in zip(
                self.layout.value.name, self.layout.value.visible):
            if not visible:
                invisible.append(name)

        # Add fields from parts that aren't invisible
        for part_name in self.parts:
            if part_name not in invisible:
                for data in self.part_fields[part_name]:
                    yield data

        # Find the exportable fields for each part
        # TODO: why not only look at visible here?
        part_info = self.run_hook(self.ReportExportable,
                                  self.create_part_contexts(only_visible=False))
        # {part_name: [ExportableInfo()]
        exportable = ExportableInfo.filter_parts(part_info)

        # Add exported fields from visible parts
        for name, export_name in zip(
                self.exports.value.name, self.exports.value.exportName):
            part_name, field_name = name.rsplit(".", 1)
            # If part is invisible, don't report it
            if part_name in invisible:
                continue
            if export_name == "":
                export_name = field_name
            exportable_infos = [x for x in exportable.get(part_name, [])
                                if field_name == x.name]
            assert len(exportable_infos), \
                "No (or multiple) ExportableInfo for %s" % name
            export, setter = self._make_export_field(exportable_infos[0])
            yield export_name, export, setter

    def _make_export_field(self, exportable_info):
        controller = self.process.get_controller(exportable_info.mri)
        path = [exportable_info.mri, exportable_info.name]
        ret = {}

        def update_field(response):
            response = deserialize_object(response, Response)
            if not isinstance(response, Delta):
                # Return or Error is the end of our subscription, log and ignore
                self.log_debug("Export got response %r", response)
                return
            if not ret:
                # First call, create the initial object
                ret["export"] = deserialize_object(response.changes[0][1])
                context = Context("ExportContext", self.process)
                if isinstance(ret["export"], AttributeModel):
                    def setter(value):
                        context.put(path, value)
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
        self.try_stateful_function(
            ss.SAVING, ss.READY, self.do_save, params.design)

    def do_save(self, design=""):
        if not design:
            design = self.design.value
        assert design, "Please specify save design name when saving from new"
        structure = self._save_to_structure()
        text = json_encode(structure, indent=2)
        filename = self._validated_config_filename(design)
        open(filename, "w").write(text)
        with self.changes_squashed:
            self._set_layout_names(design)
            self.design.set_value(design)
            # Now we are saved, modified should clear
            self.update_modified()

    def _set_layout_names(self, extra_name=None):
        names = []
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
        self.try_stateful_function(
            ss.LOADING, ss.READY, self.do_load, value)

    def do_load(self, value):
        filename = self._validated_config_filename(value)
        text = open(filename, "r").read()
        structure = json_decode(text)
        with self.changes_squashed:
            self._load_from_structure(structure)
            self.design.set_value(value)
            # Now we are loaded, modified should clear
            self.update_modified()

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
        self.saved_layout = self.layout.value.to_dict()
        # Add the exports table
        structure["exports"] = OrderedDict()
        for name, export_name in sorted(
                zip(self.exports.value.name, self.exports.value.exportName)):
            structure["exports"][name] = export_name
        self.saved_exports = self.exports.value.to_dict()
        # Add any structure that a child part wants to save
        part_structures = self.run_hook(
            self.Save, self.create_part_contexts(only_visible=False))
        for part_name, part_structure in sorted(part_structures.items()):
            structure[part_name] = part_structure
        return structure

    def _load_from_structure(self, structure):
        # Set the layout table
        layout_table = Table(self.layout.meta)
        for part_name, part_structure in structure.get("layout", {}).items():
            layout_table.append([
                part_name, "", part_structure["x"], part_structure["y"],
                part_structure["visible"]])
        self.set_layout(layout_table, update_block=False)
        self.saved_layout = self.layout.value.to_dict()
        # Set the exports table
        exports_table = Table(self.exports.meta)
        for name, export_name in structure.get("exports", {}).items():
            exports_table.append([name, export_name])
        self.exports.set_value(exports_table)
        self.saved_exports = self.exports.value.to_dict()
        # Run the load hook to get parts to load their own structure
        self.run_hook(self.Load, self.create_part_contexts(only_visible=False),
                      structure)
        self._update_block_endpoints()
