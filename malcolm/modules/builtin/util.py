from annotypes import Anno, Array, Union, Sequence

from malcolm.core import VMeta, Widget, group_tag, config_tag, Port, Table, \
    StateSet, DEFAULT_TIMEOUT

with Anno("Is the attribute writeable?"):
    AWriteable = bool
with Anno("If writeable, which iteration should this field be loaded/saved in?"
          " 0 means do not restore"):
    AConfig = int
with Anno("If given, which GUI group should we attach to"):
    AGroup = str
with Anno("If given, use this widget instead of the default"):
    AWidget = Widget
with Anno("If given, mark this as a Sink Port of the given type"):
    ASinkPort = Port


def set_tags(meta,  # type: VMeta
             writeable=False,  # type: AWriteable
             config=1,  # type: AConfig
             group=None,  # type: AGroup
             widget=None,  # type: AWidget
             sink_port=None,  # type: ASinkPort
             ):
    # type: (...) -> None
    tags = []
    meta.set_writeable(writeable)
    if widget is None:
        widget = meta.default_widget()
    if widget is not Widget.NONE:
        tags.append(widget.tag())
    if config and writeable:
        # We only allow config tags on writeable functions
        tags.append(config_tag(config))
    if group:
        # If we have a group then add the tag
        tags.append(group_tag(group))
    if sink_port:
        tags.append(sink_port.sink_port_tag(disconnected_value=""))
    meta.set_tags(tags)


with Anno("Names of the layout parts"):
    ANameArray = Array[str]
with Anno("Malcolm full names of child blocks"):
    AMriArray = Array[str]
with Anno("X Coordinates of child blocks"):
    AXArray = Array[float]
with Anno("Y Coordinates of child blocks"):
    AYArray = Array[float]
with Anno("Whether child blocks are visible"):
    AVisibleArray = Array[bool]
UNameArray = Union[ANameArray, Sequence[str]]
UMriArray = Union[AMriArray, Sequence[str]]
UXArray = Union[AXArray, Sequence[float]]
UYArray = Union[AYArray, Sequence[float]]
UVisibleArray = Union[AVisibleArray, Sequence[bool]]


class LayoutTable(Table):
    def __init__(self, name, mri, x, y, visible):
        # type: (UNameArray, UMriArray, UXArray, UYArray, UVisibleArray) -> None
        self.name = ANameArray(name)
        self.mri = AMriArray(mri)
        self.x = AXArray(x)
        self.y = AYArray(y)
        self.visible = AVisibleArray(visible)


with Anno("Name of the block.field to export"):
    ASourceNameArray = Array[str]
with Anno("Name of the field to export as"):
    AExportNameArray = Array[str]
USourceNameArray = Union[ASourceNameArray, Sequence[str]]
UExportNameArray = Union[AExportNameArray, Sequence[str]]


class ExportTable(Table):
    def __init__(self, source, export):
        # type: (USourceNameArray, UExportNameArray) -> None
        self.source = ASourceNameArray(source)
        self.export = AExportNameArray(export)


def wait_for_stateful_block_init(context, mri, timeout=DEFAULT_TIMEOUT):
    """Wait until a Block backed by a StatefulController has initialized

    Args:
        context (Context): The context to use to make the child block
        mri (str): The mri of the child block
        timeout (float): The maximum time to wait
    """
    context.when_matches(
        [mri, "state", "value"], StatefulStates.READY,
        bad_values=[StatefulStates.FAULT, StatefulStates.DISABLED],
        timeout=timeout)


class StatefulStates(StateSet):
    RESETTING = "Resetting"
    DISABLED = "Disabled"
    DISABLING = "Disabling"
    FAULT = "Fault"
    READY = "Ready"

    def __init__(self):
        super(StatefulStates, self).__init__()
        self.create_block_transitions()
        self.create_error_disable_transitions()

    def create_block_transitions(self):
        self.set_allowed(self.RESETTING, self.READY)

    def create_error_disable_transitions(self):
        block_states = self.possible_states[:]

        # Set transitions for standard states
        for state in block_states:
            self.set_allowed(state, self.FAULT)
            self.set_allowed(state, self.DISABLING)
        self.set_allowed(self.FAULT, self.RESETTING, self.DISABLING)
        self.set_allowed(self.DISABLING, self.FAULT, self.DISABLED)
        self.set_allowed(self.DISABLED, self.RESETTING)


class ManagerStates(StatefulStates):
    SAVING = "Saving"
    LOADING = "Loading"

    def create_block_transitions(self):
        super(ManagerStates, self).create_block_transitions()
        self.set_allowed(self.READY, self.SAVING)
        self.set_allowed(self.SAVING, self.READY)
        self.set_allowed(self.READY, self.LOADING)
        self.set_allowed(self.LOADING, self.READY)