from annotypes import Anno

from malcolm.core import Info, Alarm


with Anno("The title of the block"):
    ATitle = str


class TitleInfo(Info):
    """Used to tell the Controller the title of the block has changed"""
    def __init__(self, title):
        # type: (ATitle) -> None
        self.title = title


with Anno("The alarm that should be used for the health of the block"):
    AAlarm = Alarm


class HealthInfo(Info):
    """Used to tell the Controller a part has an alarm or not"""
    def __init__(self, alarm):
        # type: (AAlarm) -> None
        self.alarm = alarm


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
    """Info about a port and its value in a class

    Args:
        name (str): The name of the attribute
        value: Initial value
        direction (str): Direction of the port e.g. "in" or "out"
        type (str): Type of the port, e.g. "bool" or "NDArray"
        extra (str): For outports, value that will be set when port is selected,
            e.g. "PCOMP1.OUT" or "DET.STATS". For inports, value that will be
            set when port is disconnected, e.g. "" or "ZERO"
    """
    def __init__(self, name, value, direction, type, extra):
        self.name = name
        self.value = value
        assert direction in ("in", "out"), \
            "Direction should be 'in' or 'out', got %r" % direction
        self.direction = direction
        assert type in port_types, \
            "Type should be in %s, got %r" % (port_types, type)
        self.type = type
        self.extra = extra

