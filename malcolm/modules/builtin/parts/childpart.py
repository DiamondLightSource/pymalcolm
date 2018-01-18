import re

import numpy as np
from annotypes import Anno, add_call_types, TYPE_CHECKING

from malcolm.compat import OrderedDict
from malcolm.core import Part, serialize_object, Attribute, Subscribe, \
    Unsubscribe, Alarm, AlarmSeverity, AlarmStatus, APartName, PartRegistrar, \
    Hook, Port, Controller, config_tag, Response, Put
from malcolm.modules.builtin.util import StatefulStates
from ..infos import PortInfo, LayoutInfo, OutPortInfo, InPortInfo, \
    PartExportableInfo, PartModifiedInfo, NotifyDispatchInfo
from ..hooks import InitHook, HaltHook, ResetHook, LayoutHook, DisableHook, \
    AContext, APortMap, ALayoutTable, LoadHook, SaveHook, AStructure

if TYPE_CHECKING:
    from typing import Dict, Any, Set, List, Type, TypeVar
    TP = TypeVar("TP", bound=PortInfo)


with Anno("Malcolm resource id of child object"):
    AMri = str


port_tag_re = re.compile(r"(in|out)port:(.*):(.*)")


ss = StatefulStates


class ChildPart(Part):
    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(ChildPart, self).__init__(name)
        self.mri = mri  # type: str
        self.x = 0.0  # type: float
        self.y = 0.0  # type: float
        self.visible = None  # type: bool
        # {part_name: visible} saying whether part_name is visible
        self.part_visible = {}  # type: Dict[str, bool]
        # {attr_name: attr_value} of last saved/loaded structure
        self.saved_structure = {}  # type: Dict[str, Any]
        # {attr_name: modified_message} of current values
        self.modified_messages = {}  # type: Dict[str, str]
        # The controller hosting our child
        self.child_controller = None  # type: Controller
        # {id: Subscribe} for subscriptions to config tagged fields
        self.config_subscriptions = {}  # type: Dict[int, Subscribe]
        # set(attribute_name) where the attribute is a config tagged field
        # we are modifying
        self.we_modified = set()  # type: Set[str]
        # {attr_name: PortInfo}
        self.port_infos = {}  # type: Dict[str, PortInfo]
        self.registrar = None  # type: PartRegistrar

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.registrar = registrar
        self.registrar.report(NotifyDispatchInfo(self.notify_dispatch_request))

    def notify_dispatch_request(self, request):
        """Will be called when a context passed to a hooked function is about
        to dispatch a request"""
        if isinstance(request, Put):
            # This means the context we were passed has just made a Put request
            # so mark the field as "we_modified" so it doesn't screw up the
            # modified led
            self.we_modified.add(request.path[-2])

    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(hook, InitHook):
            hook.run(self.init)
        elif isinstance(hook, HaltHook):
            hook.run(self.halt)
        elif isinstance(hook, LayoutHook):
            hook.run(self.layout)
        elif isinstance(hook, LoadHook):
            hook.run(self.load)
        elif isinstance(hook, SaveHook):
            hook.run(self.save)
        elif isinstance(hook, DisableHook):
            hook.run(self.disable)
        elif isinstance(hook, ResetHook):
            hook.run(self.reset)

    @add_call_types
    def init(self, context):
        # type: (AContext) -> None
        if "state" in context.block_view(self.mri):
            # Wait for a while until the child is ready as it changes the
            # save state
            context.when_matches(
                [self.mri, "state", "value"], ss.READY,
                [ss.FAULT, ss.DISABLED])
        # Save what we have
        self.save(context)
        # Monitor the child configure for changes
        self.child_controller = context.get_controller(self.mri)
        subscribe = Subscribe(path=[self.mri, "meta", "fields"])
        subscribe.set_callback(self.update_part_exportable)
        # Wait for the first update to come in
        self.child_controller.handle_request(subscribe).wait()

    @add_call_types
    def disable(self, context):
        # TODO: do we actually want to disable children on disable?
        child = context.block_view(self.mri)
        if "disable" in child and child.disable.writeable:
            child.disable()

    @add_call_types
    def reset(self, context):
        child = context.block_view(self.mri)
        if "reset" in child and child.reset.writeable:
            child.reset()

    @add_call_types
    def halt(self):
        # type: () -> None
        unsubscribe = Unsubscribe(callback=self.update_part_exportable)
        self.child_controller.handle_request(unsubscribe)

    @add_call_types
    def layout(self, context, port_map, layout_table):
        # type: (AContext, APortMap, ALayoutTable) -> List[LayoutInfo]
        # if this is the first call, we need to calculate if we are visible
        # or not
        if self.visible is None:
            self.visible = self.child_connected(port_map)
        for i, name in enumerate(layout_table.name):
            x = layout_table.x[i]
            y = layout_table.y[i]
            visible = layout_table.visible[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_inports(context, port_map)
                self.x = x
                self.y = y
                self.visible = visible
            else:
                was_visible = self.part_visible.get(name, True)
                if was_visible and not visible:
                    self.sever_inports(context, port_map, name)
                self.part_visible[name] = visible
        ret = LayoutInfo(
            mri=self.mri, x=self.x, y=self.y, visible=self.visible)
        return [ret]

    @add_call_types
    def load(self, context, structure):
        # type: (AContext, AStructure) -> None
        child = context.block_view(self.mri)
        params = {}
        for k, v in structure.items():
            try:
                attr = getattr(child, k)
            except AttributeError:
                self.log.warning("Cannot restore non-existant attr %s" % k)
            else:
                try:
                    np.testing.assert_equal(serialize_object(attr.value), v)
                except AssertionError:
                    params[k] = v
        # Do this first so that any callbacks that happen in the put know
        # not to notify controller
        self.saved_structure = structure
        if params:
            child.put_attribute_values(params)

    @add_call_types
    def save(self, context):
        # type: (AContext) -> AStructure
        child = context.block_view(self.mri)
        part_structure = OrderedDict()
        for k in child:
            attr = getattr(child, k)
            if isinstance(attr, Attribute) and "config" in attr.meta.tags:
                part_structure[k] = serialize_object(attr.value)
        self.saved_structure = part_structure
        return part_structure

    def update_part_exportable(self, response):
        # type: (Response) -> None
        # Get a child context to check if we have a config field
        child = self.child_controller.block_view()
        spawned = []
        if response.value:
            new_fields = response.value
        else:
            new_fields = []

        # Remove any existing subscription that is not in the new fields
        for subscribe in self.config_subscriptions.values():
            attr_name = subscribe.path[-2]
            if attr_name not in new_fields:
                unsubscribe = Unsubscribe(subscribe.id, subscribe.callback)
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
                            info = OutPortInfo(name=field, port=Port[port],
                                               connected_value=extra)
                        else:
                            info = InPortInfo(name=field, port=Port[port],
                                              disconnected_value=extra,
                                              value=attr.value)
                        self.port_infos[field] = info
            if isinstance(attr, Attribute) and config_tag() in attr.meta.tags:
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
            if name in self.we_modified:
                message = "(We modified) " + message
            self.modified_messages[name] = message
        else:
            self.modified_messages.pop(name, None)
        message_list = []
        only_modified_by_us = True
        # Tell the controller what has changed
        for name, message in self.modified_messages.items():
            if name not in self.we_modified:
                only_modified_by_us = False
            message_list.append(message)
        if message_list:
            if only_modified_by_us:
                severity = AlarmSeverity.NO_ALARM
            else:
                severity = AlarmSeverity.MINOR_ALARM
            alarm = Alarm(
                severity, AlarmStatus.CONF_STATUS, "\n".join(message_list))
        else:
            alarm = None
        self.registrar.report(PartModifiedInfo(alarm))

    def _get_flowgraph_ports(self, port_map, typ):
        # type: (APortMap, Type[TP]) -> Dict[str, TP]
        ports = {}
        for port_info in port_map.get(self.name, []):
            if isinstance(port_info, typ):
                ports[port_info.name] = port_info
        return ports

    def _outport_lookup(self, info_list):
        # type: (List[PortInfo]) -> Dict[str, Port]
        outport_lookup = {}
        for info in info_list:
            if isinstance(info, OutPortInfo):
                outport_lookup[info.connected_value] = info.type
        return outport_lookup

    def sever_inports(self, context, port_map, connected_to=None):
        # type: (AContext, APortMap, str) -> None
        """Conditionally sever inports of the child. If connected_to is then
        None then sever all, otherwise restrict to connected_to's outports

        Args:
            context (Context): The context to use
            port_map (dict): {part_name: [PortInfo]}
            connected_to (str): Restrict severing to this part
        """
        # Find the outports to connect to
        if connected_to:
            # Calculate a lookup of the outport "name" to type
            outport_lookup = self._outport_lookup(
                port_map.get(connected_to, []))
        else:
            outport_lookup = True

        # Find our inports
        inports = self._get_flowgraph_ports(port_map, OutPortInfo)

        # If we have inports that need to be disconnected then do so
        if inports and outport_lookup:
            child = context.block_view(self.mri)
            attribute_values = {}
            for name, port_info in inports.items():
                if outport_lookup is True or outport_lookup.get(
                        child[name].value, None) == port_info.type:
                    attribute_values[name] = port_info.extra
            child.put_attribute_values(attribute_values)

    def child_connected(self, port_map):
        # type: (APortMap) -> bool
        """Calculate if anything is connected to us or we are connected to
        anything else

        Args:
            port_map: {part_name: [PortInfo]} from other ports

        Returns:
            True if we are connected or have nothing to connect
        """
        has_ports = False
        # See if our inports are connected to anything
        inports = self._get_flowgraph_ports(port_map, InPortInfo)
        for name, inport_info in inports.items():
            has_ports = True
            if inport_info.value != inport_info.disconnected_value:
                return True
        # Calculate a lookup of outport "name" to their types
        outport_lookup = self._outport_lookup(port_map.get(self.name, []))
        if outport_lookup:
            has_ports = True
        # See if anything is connected to one of our outports
        for inport_info in InPortInfo.filter_values(port_map):
            if outport_lookup.get(inport_info.value, None) == inport_info.type:
                return True
        # If we have ports and they haven't been connected to anything then
        # we are disconnected
        if has_ports:
            return False
        # otherwise, treat a block with no ports as connected
        else:
            return True
