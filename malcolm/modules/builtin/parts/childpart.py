import numpy as np
from annotypes import Anno, add_call_types, TYPE_CHECKING

from malcolm.compat import OrderedDict, clean_repr
from malcolm.core import Part, serialize_object, Attribute, Subscribe, \
    Unsubscribe, APartName, Port, Controller, Response, DEFAULT_TIMEOUT, \
    get_config_tag, Update, Return
from ..infos import PortInfo, LayoutInfo, SourcePortInfo, SinkPortInfo, \
    PartExportableInfo, PartModifiedInfo
from ..hooks import InitHook, HaltHook, ResetHook, LayoutHook, DisableHook, \
    AContext, APortMap, ALayoutTable, LoadHook, SaveHook, AStructure, \
    ULayoutInfos
from ..util import StatefulStates, wait_for_stateful_block_init

if TYPE_CHECKING:
    from typing import Dict, Any, List, Type, TypeVar, Tuple

    TP = TypeVar("TP", bound=PortInfo)


with Anno("Malcolm resource id of child object"):
    AMri = str
with Anno("Whether the part is initially visible with no config loaded, None "
          "means only if child Source/Sink Ports connect to another Block"):
    AInitialVisibility = bool
with Anno("If the child is a StatefulController then this should be True"):
    AStateful = bool


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
            wait_for_stateful_block_init(context, self.mri)
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
                    self.sever_sink_ports(context, ports)
                self.x = layout.x[i]
                self.y = layout.y[i]
                self.visible = visible
            else:
                was_visible = self.part_visibility.get(name, False)
                if was_visible and not visible:
                    self.sever_sink_ports(context, ports, name)
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
            except KeyError:
                self.log.warning("Cannot restore non-existant attr %s" % k)
            else:
                tag = get_config_tag(attr.meta.tags)
                if tag:
                    iteration = int(tag.split(":")[1])
                    iterations.setdefault(iteration, {})[k] = (attr, v)
                else:
                    self.log.warning(
                        "Attr %s is not config tagged, not restoring" % k)
        # Do this first so that any callbacks that happen in the put know
        # not to notify controller
        self.saved_structure = structure
        for name, params in sorted(iterations.items()):
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
        if isinstance(response, Update):
            new_fields = response.value
        elif isinstance(response, Return):
            # We got a return with None, so clear out all of the
            # config_subscriptions
            new_fields = []
        else:
            self.log.warning("Got unexpected response %s", response)
            return

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
                port_info = Port.port_tag_details(attr.meta.tags)
                if port_info:
                    is_source, port, extra = port_info
                    if is_source:
                        info = SourcePortInfo(
                            name=field, port=port, connected_value=extra)
                    else:
                        info = SinkPortInfo(
                            name=field, port=port, disconnected_value=extra,
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
        if isinstance(response, Update):
            subscribe = self.config_subscriptions[response.id]
            name = subscribe.path[-2]
            self.send_modified_info_if_not_equal(name, response.value)
        elif not isinstance(response, Return):
            self.log.warning("Got unexpected response %r", response)

    def send_modified_info_if_not_equal(self, name, new_value):
        original_value = self.saved_structure[name]
        try:
            np.testing.assert_equal(original_value, new_value)
        except AssertionError:
            message = "%s.%s.value = %s not %s" % (
                self.name, name, clean_repr(new_value),
                clean_repr(original_value))
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

    def _source_port_lookup(self, info_list):
        # type: (List[PortInfo]) -> Dict[str, Port]
        source_port_lookup = {}
        for info in info_list:
            if isinstance(info, SourcePortInfo):
                source_port_lookup[info.connected_value] = info.port
        return source_port_lookup

    def sever_sink_ports(self, context, ports, connected_to=None):
        # type: (AContext, APortMap, str) -> None
        """Conditionally sever Sink Ports of the child. If connected_to
        is then None then sever all, otherwise restrict to connected_to's
        Source Ports

        Args:
            context (Context): The context to use
            ports (dict): {part_name: [PortInfo]}
            connected_to (str): Restrict severing to this part
        """
        # Find the Source Ports to connect to
        if connected_to:
            # Calculate a lookup of the Source Port "name" to type
            source_port_lookup = self._source_port_lookup(
                ports.get(connected_to, []))
        else:
            source_port_lookup = True

        # Find our Sink Ports
        sink_ports = self._get_flowgraph_ports(ports, SinkPortInfo)

        # If we have Sunk Ports that need to be disconnected then do so
        if sink_ports and source_port_lookup:
            child = context.block_view(self.mri)
            attribute_values = {}
            for name, port_info in sink_ports.items():
                if source_port_lookup is True or source_port_lookup.get(
                        child[name].value, None) == port_info.port:
                    attribute_values[name] = port_info.disconnected_value
            child.put_attribute_values(attribute_values)

    def calculate_part_visibility(self, ports):
        # type: (APortMap) -> None
        """Calculate what is connected to what

        Args:
            ports: {part_name: [PortInfo]} from other ports
        """
        # Calculate a lookup of Source Port connected_value to part_name
        source_port_lookup = {}
        for part_name, port_infos in SourcePortInfo.filter_parts(ports).items():
            for port_info in port_infos:
                source_port_lookup[port_info.connected_value] = (
                    part_name, port_info.port)
        # Look through all the Sink Ports, and set both ends of the
        # connection to visible if they aren't specified
        for part_name, port_infos in SinkPortInfo.filter_parts(
                ports).items():
            for port_info in port_infos:
                if port_info.value != port_info.disconnected_value:
                    conn_part, port = source_port_lookup.get(
                        port_info.value, (None, None))
                    if conn_part and port == port_info.port:
                        if conn_part not in self.part_visibility:
                            self.part_visibility[conn_part] = True
                        if part_name not in self.part_visibility:
                            self.part_visibility[part_name] = True
