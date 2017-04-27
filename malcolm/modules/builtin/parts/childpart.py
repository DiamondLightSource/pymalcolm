import re

from malcolm.compat import OrderedDict
from malcolm.core import Part, REQUIRED, method_takes, serialize_object, \
    Attribute, Subscribe, Unsubscribe
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.builtin.infos import ExportableInfo, PortInfo, \
    LayoutInfo, ModifiedInfo
from malcolm.modules.builtin.vmetas import StringMeta


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
        # The controller hosting our child
        self.child_controller = None
        # {id: Subscribe} for subscriptions to config tagged fields
        self.config_subscriptions = {}
        # Store params
        self.params = params
        # Don't do first update
        self._do_update = False
        super(ChildPart, self).__init__(params.name)

    @ManagerController.Init
    def init(self, context):
        # Save what we have
        self.save(context)
        # Monitor the child configure for changes
        self.child_controller = context.get_controller(self.params.mri)
        subscribe = Subscribe(path=[self.params.mri, "meta", "fields"],
                              callback=self.update_exportable)
        # Wait for the first update to come in
        self.child_controller.handle_request(subscribe).wait()

    @ManagerController.Halt
    def halt(self, context):
        unsubscribe = Unsubscribe(callback=self.update_exportable)
        self.child_controller.handle_request(unsubscribe)

    @ManagerController.ReportPorts
    def report_ports(self, context):
        child = context.block_view(self.params.mri)
        port_infos = []
        for attr_name in child:
            attr = getattr(child, attr_name)
            if isinstance(attr, Attribute):
                for tag in attr.meta.tags:
                    match = port_tag_re.match(tag)
                    if match:
                        d, type, extra = match.groups()
                        port_infos.append(PortInfo(
                            name=attr_name, value=attr.value, direction=d,
                            type=type, extra=extra))
        return port_infos

    def update_exportable(self, response):
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

        # Add a subscription to any new field
        existing_fields = set(
            s.path[-2] for s in self.config_subscriptions.values())
        for field in set(new_fields) - existing_fields:
            attr = getattr(child, field)
            if isinstance(attr, Attribute) and "config" in attr.meta.tags:
                if self.config_subscriptions:
                    new_id = max(self.config_subscriptions) + 1
                else:
                    new_id = 1
                subscribe = Subscribe(id=new_id,
                                      path=[self.params.mri, field, "value"],
                                      callback=self.update_modified)
                self.config_subscriptions[new_id] = subscribe
                # Signal that any change we get is a difference
                if field not in self.saved_structure:
                    self.saved_structure[field] = None
                spawned.append(
                    self.child_controller.handle_request(subscribe))

        # Wait for the first update to come in
        for s in spawned:
            s.wait()

        # Tell the controller we have new fields to export unless at init
        if self._do_update:
            self.controller.update_exportable()
        else:
            self._do_update = True

    def update_modified(self, response):
        # Ignore initial updates
        if self._do_update:
            # Tell the controller to update if the value has changed from saved
            subscribe = self.config_subscriptions[response.id]
            attr = subscribe.path[-2]
            if self.saved_structure[attr] != response.value:
                self.controller.update_modified()

    @ManagerController.ReportExportable
    def report_exportable(self, context):
        child = context.block_view(self.params.mri)
        ret = []
        for name in child:
            if name != "meta":
                ret.append(ExportableInfo(name=name, mri=self.params.mri))
        return ret

    @ManagerController.ReportModified
    def report_modified(self, context):
        child = context.block_view(self.params.mri)
        ret = []
        for name, original_value in self.saved_structure.items():
            attr = getattr(child, name)
            if isinstance(attr, Attribute) and "config" in attr.meta.tags:
                current_value = serialize_object(attr.value)
                if original_value != current_value:
                    ret.append(
                        ModifiedInfo(name, original_value, current_value))
        return ret

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
                was_visible = self.part_visible.get(name, True)
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
            except KeyError:
                self.log.warning("Cannot restore non-existant attr %s" % k)
            else:
                assert "config" in attr.meta.tags, \
                    "Attr %s doesn't have config tag" % k
                if attr.value != v:
                    params[k] = v
        # Do this first so that any callbacks that happen in the put know
        # not to notify controller
        self.saved_structure = part_structure

        # Don't update while we're putting values or we'll deadlock
        self._do_update = False
        child.put_attribute_values(params)
        self._do_update = True

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
            # Don't update while we're putting values or we'll deadlock
            self._do_update = False
            child.put_attribute_values(attribute_values)
            self._do_update = True

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
