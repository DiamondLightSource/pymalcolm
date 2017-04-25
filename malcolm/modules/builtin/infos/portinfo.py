from malcolm.core import Info
from malcolm.tags import port_types


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
