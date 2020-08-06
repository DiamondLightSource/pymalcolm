import collections.abc
from typing import TYPE_CHECKING, Iterable, Sequence, Type, Union
from xml.etree import cElementTree as ET

from annotypes import Anno, Array

from malcolm.compat import et_to_string
from malcolm.core import (
    DEFAULT_TIMEOUT,
    Port,
    StateSet,
    Table,
    VMeta,
    Widget,
    config_tag,
    group_tag,
)

if TYPE_CHECKING:
    from .parts import ChildPart  # noqa: F401

with Anno("Is the attribute writeable?"):
    AWriteable = bool
with Anno(
    "If writeable, which iteration should this field be loaded/saved in?"
    " 0 means do not restore"
):
    AConfig = int
with Anno("If given, which GUI group should we attach to"):
    AGroup = str
with Anno("If given, use this widget instead of the default"):
    AWidget = Widget
with Anno("If given, mark this as a Sink Port of the given type"):
    ASinkPort = Port
with Anno(
    "If given, mark this Sink Port as having a badge"
    + " value [tag constructed by badge_value_tag()]"
):
    APortBadge = str


def set_tags(
    meta: VMeta,
    writeable: AWriteable = False,
    config: AConfig = 1,
    group: AGroup = None,
    widget: AWidget = None,
    sink_port: ASinkPort = None,
    port_badge: APortBadge = None,
) -> None:
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
        if port_badge:
            tags.append(port_badge)
    meta.set_tags(tags)


with Anno("Names of the layout parts"):
    ANameArray = Union[Array[str]]
with Anno("Malcolm full names of child blocks"):
    AMriArray = Union[Array[str]]
with Anno("X Coordinates of child blocks"):
    AXArray = Union[Array[float]]
with Anno("Y Coordinates of child blocks"):
    AYArray = Union[Array[float]]
with Anno("Whether child blocks are visible"):
    AVisibleArray = Union[Array[bool]]
UNameArray = Union[ANameArray, Sequence[str]]
UMriArray = Union[AMriArray, Sequence[str]]
UXArray = Union[AXArray, Sequence[float]]
UYArray = Union[AYArray, Sequence[float]]
UVisibleArray = Union[AVisibleArray, Sequence[bool]]


class LayoutTable(Table):
    def __init__(
        self,
        name: UNameArray,
        mri: UMriArray,
        x: UXArray,
        y: UYArray,
        visible: UVisibleArray,
    ) -> None:
        self.name = ANameArray(name)
        self.mri = AMriArray(mri)
        self.x = AXArray(x)
        self.y = AYArray(y)
        self.visible = AVisibleArray(visible)


with Anno("Name of the block.field to export"):
    ASourceNameArray = Union[Array[str]]
with Anno("Name of the field to export as"):
    AExportNameArray = Union[Array[str]]
USourceNameArray = Union[ASourceNameArray, Sequence[str]]
UExportNameArray = Union[AExportNameArray, Sequence[str]]


class ExportTable(Table):
    def __init__(self, source: USourceNameArray, export: UExportNameArray) -> None:
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
        [mri, "state", "value"],
        StatefulStates.READY,
        bad_values=[StatefulStates.FAULT, StatefulStates.DISABLED],
        timeout=timeout,
    )


class StatefulStates(StateSet):
    """This state set covers controllers and parts that can be disabled and have
    faults, but otherwise have no state."""

    RESETTING = "Resetting"
    DISABLED = "Disabled"
    DISABLING = "Disabling"
    FAULT = "Fault"
    READY = "Ready"

    def __init__(self):
        super().__init__()
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
    """This state set covers controllers and parts that have loadable and
    savable child state."""

    SAVING = "Saving"
    LOADING = "Loading"

    def create_block_transitions(self):
        super().create_block_transitions()
        self.set_allowed(self.READY, self.SAVING)
        self.set_allowed(self.SAVING, self.READY)
        self.set_allowed(self.READY, self.LOADING)
        self.set_allowed(self.LOADING, self.READY)


def no_save(*attribute_names):
    """Helper for defining ChildPart.no_save_attribute_names.

    Args:
        attribute_names (str): The Attributes of the child Block that shouldn't
            be saved
    """

    def decorator(cls: Type["ChildPart"]) -> Type["ChildPart"]:
        additions = set()
        for attribute_name in attribute_names:
            if isinstance(attribute_name, collections.abc.Iterable) and not isinstance(
                attribute_name, str
            ):
                additions |= set(attribute_name)
            else:
                additions.add(attribute_name)
        bad = [x for x in additions if not isinstance(x, str)]
        assert not bad, "Cannot add non-string attribute names to no_save: %s" % bad
        existing = cls.no_save_attribute_names or set()
        cls.no_save_attribute_names = existing | additions
        return cls

    return decorator


class SVGIcon:
    """Helper object for working with SVG icons"""

    def __init__(self, svg_text: str) -> None:
        # https://stackoverflow.com/a/8998773
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        self.root = ET.fromstring(svg_text)

    def find_parent_child(self, id):
        child = None
        # Find the first parent which has a child with id i
        parent = self.root.find(".//*[@id=%r]/.." % id)
        # Find the child and remove it
        if parent:
            child = parent.find("./*[@id=%r]" % id)
        return parent, child

    def remove_elements(self, ids: Iterable[str]) -> None:
        for i in ids:
            parent, child = self.find_parent_child(i)
            parent.remove(child)

    def add_text(
        self, text, x=0, y=0, anchor="left", transform=None, style="font: 10px sans"
    ):
        attr = ET.SubElement(self.root, "text", x=str(x), y=str(y), style=style)
        if transform:
            attr.set("transform", transform)
        attr.set("text-anchor", anchor)
        attr.text = text

    def update_edge_arrow(self, id, edge):
        edge = edge.lower()
        parent, child = self.find_parent_child(id)
        # Check that it still exists, it might have been removed
        if parent is not None:
            if "level" in edge:
                # Remove it
                parent.remove(child)
            elif "rising" in edge:
                # Remove the falling marker
                del child.attrib["marker-end"]
            elif "falling" in edge:
                # Remove the falling marker
                del child.attrib["marker-start"]

    def __str__(self):
        return et_to_string(self.root)
