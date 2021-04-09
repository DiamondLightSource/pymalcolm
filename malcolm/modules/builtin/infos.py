from typing import Any, Dict, List, Sequence

from malcolm.core import Alarm, Info, Port, Request, TimeStamp


class LabelInfo(Info):
    """Used to tell the Controller the label of the Block should change

    Args:
        label: The new title of the Block
    """

    def __init__(self, label: str) -> None:
        self.label = label


class HealthInfo(Info):
    """Used to tell the Controller a part has an alarm or not

    Args:
        alarm: The alarm that should be used for the health of the block
    """

    def __init__(self, alarm: Alarm, ts: TimeStamp = None) -> None:
        self.alarm = alarm
        self.ts = ts


class PortInfo(Info):
    """Info about a port to be used by other child parts for connection

    Args:
        name: The name of the attribute
        port: The type of the port
    """

    def __init__(self, name: str, port: Port) -> None:
        self.name = name
        self.port = port


class SinkPortInfo(PortInfo):
    """Info about a Sink Port from the attribute tag

    Args:
        name: The name of the attribute
        port: The type of the port
        disconnected_value: The value that will be set when the Sink
            port is disconnected, E.g. '' or 'ZERO'
        value: Initial value of the attribute
    """

    def __init__(
        self, name: str, port: Port, disconnected_value: str, value: Any
    ) -> None:
        super().__init__(name, port)
        self.disconnected_value = disconnected_value
        self.value = value


class SourcePortInfo(PortInfo):
    """Info about a Source Port from the attribute tag

    Args:
        name: The name of the attribute
        port: The type of the port
        connected_value: The value that a Sink Port will be set to when
            connected to this Source Port, E.g. 'PCOMP1.OUT' or 'DET.STATS'
    """

    def __init__(self, name: str, port: Port, connected_value: str) -> None:
        super().__init__(name, port)
        self.connected_value = connected_value


class LayoutInfo(Info):
    """Info about the position and visibility of a child block in a layout

    Args:
        mri: Malcolm full name of child block
        x: X Coordinate of child block
        y: Y Coordinate of child block
        visible: Whether child block is visible
    """

    def __init__(self, mri: str, x: float, y: float, visible: bool) -> None:
        self.mri = mri
        self.x = x
        self.y = y
        self.visible = visible


class PartExportableInfo(Info):
    """Info about the exportable fields and port infos for a Part

    Args:
        names: The list of fields that the Part thinks are exportable
        port_infos: The list of PortInfo objects that the Part exposes
    """

    def __init__(self, names: Sequence[str], port_infos: List[PortInfo]) -> None:
        self.names = names
        self.port_infos = port_infos


class PartModifiedInfo(Info):
    """Info about whether the part was modified or not

    Args:
        modified: {attr_name: message} for all attributes that have been
            modified from the saved value
    """

    def __init__(self, modified: Dict[str, str]) -> None:
        self.modified = modified


class RequestInfo(Info):
    """Info saying that the part has received a request that needs servicing.
    Reporting this will send to the correct controller, but not wait for
    completion

    Args:
        request: The request that needs servicing, with callback filled in
        mri: The mri of the controller that should handle it
    """

    def __init__(self, request: Request, mri: str) -> None:
        self.request = request
        self.mri = mri
