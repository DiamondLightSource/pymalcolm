import re

import numpy as np
from annotypes import Anno, add_call_types, TYPE_CHECKING

from malcolm.compat import OrderedDict
from malcolm.core import Part, serialize_object, Attribute, Subscribe, \
    Unsubscribe, APartName, Port, Controller, Response, DEFAULT_TIMEOUT, \
    get_config_tag
from ..infos import PortInfo, LayoutInfo, OutPortInfo, InPortInfo, \
    PartExportableInfo, PartModifiedInfo
from ..hooks import InitHook, HaltHook, ResetHook, LayoutHook, DisableHook, \
    AContext, APortMap, ALayoutTable, LoadHook, SaveHook, AStructure, \
    ULayoutInfos
from ..util import StatefulStates

if TYPE_CHECKING:
    from typing import Dict, Any, List, Type, TypeVar, Tuple

    TP = TypeVar("TP", bound=PortInfo)


with Anno("Malcolm resource id of child object"):
    AMri = str
with Anno("Whether the part is initially visible with no config loaded, None "
          "means only if child in/outports are connected to another Block"):
    AInitialVisibility = bool
with Anno("If the child is a StatefulController then this should be True"):
    AStateful = bool


port_tag_re = re.compile(r"(in|out)port:(.*):(.*)")


ss = StatefulStates


class ChildPart(Part):
    def __init__(self, name, mri, initial_visibility=None, stateful=True):
        # type: (APartName, AMri, AInitialVisibility, AStateful) -> None
        super(ChildPart, self).__init__(name)
        self.stateful = stateful
        self.mri = mri
        self.x = 0.0  # type: float
        self.y = 0.0  # type: float
        self.visible = initial_visibility  # type: bool
        # {part_name: visible} saying whether part_name is visible
        self.part_visibility = {}  # type: Dict[str, bool]
        # {attr_name: attr_value} of last saved/loaded structure
        self.saved_structure = {}  # type: Dict[str, Any]
        # {attr_name: modified_message} of current values
        self.modified_messages = {}  # type: Dict[str, str]
        # The controller hosting our child
        self.child_controller = None  # type: Controller
        # {id: Subscribe} for subscriptions to config tagged fields
        self.config_subscriptions = {}  # type: Dict[int, Subscribe]
        # {attr_name: PortInfo}
        self.port_infos = {}  # type: Dict[str, PortInfo]
        # Hooks
        self.register_hooked(InitHook, self.init)
        self.register_hooked(HaltHook, self.halt)
        self.register_hooked(LayoutHook, self.layout)
        self.register_hooked(LoadHook, self.load)
        self.register_hooked(SaveHook, self.save)
        self.register_hooked(DisableHook, self.disable)
        self.register_hooked(ResetHook, self.reset)

    @add_call_types
    def init(self, context):
        # type: (AContext) -> None
        self.child_controller = context.get_controller(self.mri)
        if self.stateful:
            # Wait for a while until the child is ready as it changes the
            # save state
            context.when_matches(
                [self.mri, "state", "value"], ss.READY,
                [ss.FAULT, ss.DISABLED], timeout=DEFAULT_TIMEOUT)
        # Save what we have
        self.save(context)
        subscribe = Subscribe(path=[self.mri, "meta", "fields"])
        subscribe.set_callback(self.update_part_exportable)
        # Wait for the first update to come in
        self.child_controller.handle_request(subscribe).wait()

    @add_call_types
    def disable(self, context):
        # type: (AContext) -> None
        # TODO: do we actually want to disable children on disable?
        child = context.block_view(self.mri)
        if self.stateful and child.disable.writeable:
            child.disable()

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        if self.stateful and child.reset.writeable:
            child.reset()

    @add_call_types
    def halt(self):
        # type: () -> None
        unsubscribe = Unsubscribe()
        unsubscribe.set_callback(self.update_part_exportable)
        self.child_controller.handle_request(unsubscribe)

    @add_call_types
    def layout(self, context, ports, layout):
        # type: (AContext, APortMap, ALayoutTable) -> ULayoutInfos
        first_call = not self.part_visibility
        for i, name in enumerate(layout.name):
            visible = layout.visible[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_inports(context, ports)
                self.x = layout.x[i]
                self.y = layout.y[i]
                self.visible = visible
            else:
                was_visible = self.part_visibility.get(name, False)
                if was_visible and not visible:
                    self.sever_inports(context, ports, name)
                self.part_visibility[name] = visible
        # If this is the first call work out which parts are visible if not
        # specified in the initial layout table
        if first_call:
            self.calculate_part_visibility(ports)
        # If not specified then take our own visibility from this same dict
        if self.visible is None:
            self.visible = self.part_visibility.get(self.name, False)
        ret = LayoutInfo(
            mri=self.mri, x=self.x, y=self.y, visible=self.visible)
        return [ret]

    @add_call_types
    def load(self, context, structure):
        # type: (AContext, AStructure) -> None
        child = context.block_view(self.mri)
        iterations = {}  # type: Dict[int, Dict[str, Tuple[Attribute, Any]]]
        for k, v in structure.items():
            try:
                attr = getattr(child, k)
            except AttributeError:
                self.log.warning("Cannot restore non-existant attr %s" % k)
            else:
                tag = get_config_tag(attr.meta.tags)
                if tag:
                    iteration = int(tag.split(":")[1])
                    iterations.setdefault(iteration, {})[k] = (attr, v)
                else:
                    self.log.warning("Attr %s is not config tagged" % k)
        # Do this first so that any callbacks that happen in the put know
        # not to notify controller
        self.saved_structure = structure
        # TODO: only load design if visible and not at init
        for _, params in sorted(iterations.items()):
            # Call each iteration as a separate operation, only putting the
            # ones that need to change
            to_set = {}
            for k, (attr, v) in params.items():
                try:
                    np.testing.assert_equal(serialize_object(attr.value), v)
                except AssertionError:
                    to_set[k] = v
            child.put_attribute_values(to_set)

    @add_call_types
    def save(self, context):
        # type: (AContext) -> AStructure
        child = context.block_view(self.mri)
        part_structure = OrderedDict()
        for k in child:
            attr = getattr(child, k)
            if isinstance(attr, Attribute) and get_config_tag(attr.meta.tags):
                part_structure[k] = serialize_object(attr.value)
        self.saved_structure = part_structure
        return part_structure

    def update_part_exportable(self, response):
        # type: (Response) -> None
        # Get a child context to check if we have a config field
        child = self.child_controller.make_view()
        spawned = []
        if response.value:
            new_fields = response.value
        else:
            new_fields = []

        # Remove any existing subscription that is not in the new fields
        for subscribe in self.config_subscriptions.values():
            attr_name = subscribe.path[-2]
            if attr_name not in new_fields:
                unsubscribe = Unsubscribe(subscribe.id)
                unsubscribe.set_callback(subscribe.callback)
                spawned.append(
                    self.child_controller.handle_request(unsubscribe))
                self.port_infos.pop(attr_name, None)

        # Add a subscription to any new field
        existing_fields = set(
            s.path[-2] for s in self.config_subscriptions.values())
        for field in set(new_fields) - existing_fields:
            attr = getattr(child, field)
            if isinstance(attr, Attribute):
                for tag in attr.meta.tags:
                    match = port_tag_re.match(tag)
                    if match:
                        d, port, extra = match.groups()
                        if d == "out":
                            info = OutPortInfo(name=field, port=Port(port),
                                               connected_value=extra)
                        else:
                            info = InPortInfo(name=field, port=Port(port),
                                              disconnected_value=extra,
                                              value=attr.value)
                        self.port_infos[field] = info
            if isinstance(attr, Attribute) and get_config_tag(attr.meta.tags):
                if self.config_subscriptions:
                    new_id = max(self.config_subscriptions) + 1
                else:
                    new_id = 1
                subscribe = Subscribe(id=new_id,
                                      path=[self.mri, field, "value"])
                subscribe.set_callback(self.update_part_modified)
                self.config_subscriptions[new_id] = subscribe
                # Signal that any change we get is a difference
                if field not in self.saved_structure:
                    self.saved_structure[field] = None
                spawned.append(
                    self.child_controller.handle_request(subscribe))

        # Wait for the first update to come in
        for s in spawned:
            s.wait()

        # Put data on the queue, so if spawns are handled out of order we
        # still get the most up to date data
        port_infos = [
            self.port_infos[f] for f in new_fields if f in self.port_infos]
        self.registrar.report(PartExportableInfo(new_fields, port_infos))

    def update_part_modified(self, response):
        # type: (Response) -> None
        subscribe = self.config_subscriptions[response.id]
        name = subscribe.path[-2]
        original_value = self.saved_structure[name]
        try:
            np.testing.assert_equal(original_value, response.value)
        except AssertionError:
            message = "%s.%s.value = %r not %r" % (
                self.name, name, response.value, original_value)
        else:
            message = None
        last_message = self.modified_messages.get(name, None)
        if message != last_message:
            # Tell the controller if something has changed
            if message:
                self.modified_messages[name] = message
            else:
                self.modified_messages.pop(name, None)
            info = PartModifiedInfo(self.modified_messages.copy())
            self.registrar.report(info)

    def _get_flowgraph_ports(self, ports, typ):
        # type: (APortMap, Type[TP]) -> Dict[str, TP]
        ret = {}
        for port_info in ports.get(self.name, []):
            if isinstance(port_info, typ):
                ret[port_info.name] = port_info
        return ret

    def _outport_lookup(self, info_list):
        # type: (List[PortInfo]) -> Dict[str, Port]
        outport_lookup = {}
        for info in info_list:
            if isinstance(info, OutPortInfo):
                outport_lookup[info.connected_value] = info.port
        return outport_lookup

    def sever_inports(self, context, ports, connected_to=None):
        # type: (AContext, APortMap, str) -> None
        """Conditionally sever inports of the child. If connected_to is then
        None then sever all, otherwise restrict to connected_to's outports

        Args:
            context (Context): The context to use
            ports (dict): {part_name: [PortInfo]}
            connected_to (str): Restrict severing to this part
        """
        # Find the outports to connect to
        if connected_to:
            # Calculate a lookup of the outport "name" to type
            outport_lookup = self._outport_lookup(
                ports.get(connected_to, []))
        else:
            outport_lookup = True

        # Find our inports
        inports = self._get_flowgraph_ports(ports, InPortInfo)

        # If we have inports that need to be disconnected then do so
        if inports and outport_lookup:
            child = context.block_view(self.mri)
            attribute_values = {}
            for name, port_info in inports.items():
                if outport_lookup is True or outport_lookup.get(
                        child[name].value, None) == port_info.port:
                    attribute_values[name] = port_info.disconnected_value
            child.put_attribute_values(attribute_values)

    def calculate_part_visibility(self, ports):
        # type: (APortMap) -> None
        """Calculate what is connected to what

        Args:
            ports: {part_name: [PortInfo]} from other ports
        """
        # Calculate a lookup of outport connected_value to part_name
        outport_lookup = {}
        for part_name, port_infos in OutPortInfo.filter_parts(ports).items():
            for port_info in port_infos:
                outport_lookup[port_info.connected_value] = (
                    part_name, port_info.port)
        # Look through all the inports, and set both ends of the connection
        # to visible if they aren't specified
        for part_name, port_infos in InPortInfo.filter_parts(ports).items():
            for port_info in port_infos:
                if port_info.value != port_info.disconnected_value:
                    conn_part, port = outport_lookup.get(
                        port_info.value, (None, None))
                    if conn_part and port == port_info.port:
                        if conn_part not in self.part_visibility:
                            self.part_visibility[conn_part] = True
                        if part_name not in self.part_visibility:
                            self.part_visibility[part_name] = True
