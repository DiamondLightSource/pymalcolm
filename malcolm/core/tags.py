from enum import Enum
from annotypes import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence, Union


def group_tag(group_name):
    # type: (str) -> str
    """Marks this field as belonging to a group"""
    tag = "group:%s" % group_name
    return tag


def config_tag(iteration=1):
    # type: (int) -> str
    """Marks this field as a value that should be saved and loaded at config

    Args:
        iteration: All iterations are sorted in increasing order and done in
            batches of the same iteration number
    """
    tag = "config:%d" % iteration
    return tag


def get_config_tag(tags):
    # type: (Sequence[str]) -> Union[str, None]
    """Get the config_tag from tags or return None"""
    for tag in tags:
        if tag.startswith("config:"):
            return tag


class Widget(Enum):
    """Enum with all the known widget tags to appear on Attribute Metas"""
    NONE = ""  # Force no widget
    TEXTINPUT = "textinput"  # Editable text input box
    TEXTUPDATE = "textupdate"  # Read only text update
    LED = "led"  # On/Off LED indicator
    COMBO = "combo"  # Select from a number of choice values
    ICON = "icon"  # This field gives the URL for an icon for the whole Block
    GROUP = "group"  # Group node in a TreeView that other fields can attach to
    TABLE = "table"  # Table of rows. A list is a single column table
    CHECKBOX = "checkbox"  # A box that can be checked or not
    FLOWGRAPH = "flowgraph"  # Boxes with lines for child block connections
    TITLE = "title"  # This widget should be used as the title of the page

    def tag(self):
        assert self != Widget.NONE, "Widget.NONE has no widget tag"
        return "widget:%s" % self.value


class Port(Enum):
    """Enum with all the known flowgraph port tags to appear on Attribute
    Metas"""
    BOOL = "bool"  # Boolean
    INT32 = "int32"  # 32-bit signed integer
    NDARRAY = "NDArray"  # areaDetector NDArray port
    MOTOR = "motor"  # motor record connection to CS or controller

    def inport_tag(self, disconnected_value):
        return "inport:%s:%s" % (self.value, disconnected_value)

    def outport_tag(self, connected_value):
        return "outport:%s:%s" % (self.value, connected_value)
