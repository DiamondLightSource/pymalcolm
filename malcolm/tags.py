widget_types = [
    "textinput",  # Editable text input box
    "textupdate",  # Read only text update
    "led",  # On/Off LED indicator
    "combo",  # Select from a number of choice values
    "icon",  # This field gives the URL for an icon for the whole Block
    "group",  # This is a group in a TreeView that other fields can attach to
    # TODO: what about the standard state/status etc?
    "action",  # This is an action button that should always be visible
    "table",  # This is a table of rows
    "checkbox",  # This is a box that can be checked or not
]


def widget(widget_type):
    """Associates a widget with this field"""
    assert widget_type in widget_types, \
        "Got %r, expected one of %s" % (widget_type, widget_types)
    tag = "widget:%s" % widget_type
    return tag


port_types = [
    "bool",  # Boolean
    "int32",  # 32-bit signed integer
    "NDArray",  # areaDetector NDArray port
    "CS",  # Motor co-ordinate system
]


def inport(port_type, disconnected_value):
    """Marks this field as an inport"""
    assert port_type in port_types, \
        "Got %r, expected one of %s" % (port_type, port_types)
    tag = "inport:%s:%s" % (port_type, disconnected_value)
    return tag


def outport(port_type, connected_value):
    """Marks this field as an outport"""
    assert port_type in port_types, \
        "Got %r, expected one of %s" % (port_type, port_types)
    tag = "outport:%s:%s" % (port_type, connected_value)
    return tag


def group(group_name):
    """Marks this field as belonging to a group"""
    tag = "group:%s" % group_name
    return tag


def config():
    """Marks this field as a value that should be saved and loaded at config"""
    tag = "config"
    return tag
