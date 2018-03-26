import re

import numpy as np

from malcolm.compat import OrderedDict
from malcolm.core import Part, REQUIRED, method_takes, serialize_object, \
    Attribute, Subscribe, Unsubscribe, Put, Alarm, AlarmSeverity, AlarmStatus, \
    Queue
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.builtin.infos import PortInfo, LayoutInfo
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.tags import config


port_tag_re = re.compile(r"(in|out)port:(.*):(.*)")


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED,
    "mri", StringMeta("Malcolm resource id of child object"), REQUIRED)
class ChildPart(Part):
    def __init__(self, params):
        # Layout options
        self.x = 0
        self.y = 0
        self.visible = None
        # {part_name: visible} saying whether part_name is visible
        self.part_visible = {}
        # {attr_name: attr_value} of last saved/loaded structure
        self.saved_structure = {}
        # {attr_name: modified_message} of current values
        self.modified_messages = {}
        # The controller hosting our child
        self.child_controller = None
        # {id: Subscribe} for subscriptions to config tagged fields
        self.config_subscriptions = {}
        # set(attribute_name) where the attribute is a config tagged field
        # we are modifying
        self.we_modified = set()
        # Update queue of modified alarms
        self.modified_update_queue = Queue()
        # Update queue of exportable fields
        self.exportable_update_queue = Queue()
        # {attr_name: PortInfo}
        self.port_infos = {}
        # Store params
        self.params = params
        super(ChildPart, self).__init__(params.name)

    def notify_dispatch_request(self, request):
        """Will be called when a context passed to a hooked function is about
        to dispatch a request"""
        if isinstance(request, Put):
            self.we_modified.add(request.path[-2])

    @ManagerController.Init
    def init(self, context):
        # Save what we have
        self.save(context)
        # Monitor the child configure for changes
        self.child_controller = context.get_controller(self.params.mri)
        subscribe = Subscribe(path=[self.params.mri, "meta", "fields"],
                              callback=self.update_part_exportable)
        # Wait for the first update to come in
        self.child_controller.handle_request(subscribe).wait()

    @ManagerController.Halt
    def halt(self, context):
        unsubscribe = Unsubscribe(callback=self.update_part_exportable)
        self.child_controller.handle_request(unsubscribe)

    def update_part_exportable(self, response):
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
                        d, type, extra = match.groups()
                        self.port_infos[field] = PortInfo(
                            name=field, value=attr.value, direction=d,
                            type=type, extra=extra)
            if isinstance(attr, Attribute) and config() in attr.meta.tags:
                if self.config_subscriptions:
                    new_id = max(self.config_subscriptions) + 1
                else:
                    new_id = 1
                subscribe = Subscribe(id=new_id,
                                      path=[self.params.mri, field, "value"],
                                      callback=self.update_part_modified)
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
        self.exportable_update_queue.put((new_fields, port_infos))
        self.spawn(self._update_part_exportable).wait()

    def _update_part_exportable(self):
        # We spawned just above, so there is definitely something on the
        # queue
        fields, port_infos = self.exportable_update_queue.get(timeout=0)
        self.controller.update_exportable(self, fields, port_infos)

    def update_part_modified(self, response):
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
        # Put data on the queue, so if spawns are handled out of order we
        # still get the most up to date data
        self.modified_update_queue.put(alarm)
        self.spawn(self._update_part_modified).wait()

    def _update_part_modified(self):
        # We spawned just above, so there is definitely something on the
        # queue
        alarm = self.modified_update_queue.get(timeout=0)
        self.controller.update_modified(self, alarm)

    @ManagerController.Layout
    def layout(self, context, part_info, layout_table):
        # if this is the first call, we need to calculate if we are visible
        # or not
        if self.visible is None:
            self.visible = self.child_connected(part_info)
        for i, name in enumerate(layout_table.name):
            x = layout_table.x[i]
            y = layout_table.y[i]
            visible = layout_table.visible[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_inports(context, part_info)
                self.x = x
                self.y = y
                self.visible = visible
            else:
                was_visible = self.part_visible.get(name, False)
                if was_visible and not visible:
                    self.sever_inports(context, part_info, name)
                self.part_visible[name] = visible
        ret = LayoutInfo(
            mri=self.params.mri, x=self.x, y=self.y, visible=self.visible)
        return [ret]

    @ManagerController.Load
    def load(self, context, structure):
        child = context.block_view(self.params.mri)
        part_structure = structure.get(self.name, {})
        params = {}
        for k, v in part_structure.items():
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
        self.saved_structure = part_structure
        if params:
            child.put_attribute_values(params)

    @ManagerController.Save
    def save(self, context):
        child = context.block_view(self.params.mri)
        part_structure = OrderedDict()
        for k in child:
            attr = getattr(child, k)
            if isinstance(attr, Attribute) and "config" in attr.meta.tags:
                part_structure[k] = serialize_object(attr.value)
        self.saved_structure = part_structure
        return part_structure

    def _get_flowgraph_ports(self, part_info, direction):
        # {attr_name: port_info}
        ports = {}
        for port_info in part_info.get(self.name, []):
            if port_info.direction == direction:
                ports[port_info.name] = port_info
        return ports

    def _outport_lookup(self, port_infos):
        outport_lookup = {}
        for outport_info in port_infos:
            if outport_info.direction == "out":
                outport_lookup[outport_info.extra] = outport_info.type
        return outport_lookup

    def sever_inports(self, context, part_info, connected_to=None):
        """Conditionally sever inports of the child. If connected_to is then
        None then sever all, otherwise restrict to connected_to's outports

        Args:
            context (Context): The context to use
            part_info (dict): {part_name: [PortInfo]}
            connected_to (str): Restrict severing to this part
        """
        # Find the outports to connect to
        if connected_to:
            # Calculate a lookup of the outport "name" to type
            outport_lookup = self._outport_lookup(
                part_info.get(connected_to, []))
        else:
            outport_lookup = True

        # Find our inports
        inports = self._get_flowgraph_ports(part_info, "in")

        # If we have inports that need to be disconnected then do so
        if inports and outport_lookup:
            child = context.block_view(self.params.mri)
            attribute_values = {}
            for name, port_info in inports.items():
                if outport_lookup is True or outport_lookup.get(
                        child[name].value, None) == port_info.type:
                    attribute_values[name] = port_info.extra
            child.put_attribute_values(attribute_values)

    def child_connected(self, part_info):
        """Calculate if anything is connected to us or we are connected to
        anything else

        Args:
            part_info (dict): {part_name: [PortInfo]} from other ports

        Returns:
            bool: True if we are connected or have nothing to connect
        """
        has_ports = False
        # See if our inports are connected to anything
        inports = self._get_flowgraph_ports(part_info, "in")
        for name, inport_info in inports.items():
            disconnected_value = inport_info.extra
            has_ports = True
            if inport_info.value != disconnected_value:
                return True
        # Calculate a lookup of outport "name" to their types
        outport_lookup = self._outport_lookup(part_info.get(self.name, []))
        if outport_lookup:
            has_ports = True
        # See if anything is connected to one of our outports
        for inport_info in PortInfo.filter_values(part_info):
            if inport_info.direction == "in":
                if outport_lookup.get(
                        inport_info.value, None) == inport_info.type:
                    return True
        # If we have ports and they haven't been connected to anything then
        # we are disconnected
        if has_ports:
            return False
        # otherwise, treat a block with no ports as connected
        else:
            return True
