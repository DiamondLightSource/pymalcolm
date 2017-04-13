from malcolm.compat import OrderedDict
from malcolm.controllers.builtin import ManagerController
from malcolm.infos.builtin import ExportableInfo, PortInfo, LayoutInfo, \
    ModifiedInfo
from malcolm.core import Part, REQUIRED, method_takes, serialize_object, \
    Attribute, Subscribe, Unsubscribe
from malcolm.vmetas.builtin import StringMeta


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
        port_infos = list(self._get_flowgraph_ports(child, "in").values())
        port_infos += list(self._get_flowgraph_ports(child, "out").values())
        return port_infos

    def _get_flowgraph_ports(self, child, direction):
        """Get a PortInfo for each flowgraph of the child matching a direction

        Args:
            direction (str): Which direction to get, "in" or "out"

        Returns:
            dict: {attr_name: PortInfo}: PortInfo for the requested Attributes
        """
        ports = OrderedDict()
        for attr_name in child:
            attr = getattr(child, attr_name)
            if isinstance(attr, Attribute):
                for tag in attr.meta.tags:
                    if tag.startswith("%sport" % direction):
                        direction, type, extra = tag.split(":", 3)
                        # Strip of the "port" suffix
                        direction = direction[:-4]
                        ports[attr_name] = PortInfo(
                            direction=direction, type=type, value=attr.value,
                            extra=extra)
        return ports

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
                if attr not in self.saved_structure:
                    self.saved_structure[attr] = None
                spawned.append(
                    self.child_controller.handle_request(subscribe))

        # Wait for them to finish
        for s in spawned:
            s.wait()

        # Tell the controller we have new fields to export
        self.controller.update_exportable()

    def update_modified(self, response):
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
        for name in child:
            attr = getattr(child, name)
            if isinstance(attr, Attribute) and "config" in attr.meta.tags:
                original_value = self.saved_structure[name]
                current_value = serialize_object(attr.value)
                if original_value != current_value:
                    ret.append(
                        ModifiedInfo(name, original_value, current_value))
        return ret

    @ManagerController.Layout
    def layout(self, context, part_info, layout_table):
        # if this is the first call, we need to calculate if we are visible
        # or not
        child = context.block_view(self.params.mri)
        if self.visible is None:
            self.visible = self.child_connected(child, part_info)
        for i, name in enumerate(layout_table.name):
            _, _, x, y, visible = layout_table[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_inports(child)
                self.x = x
                self.y = y
                self.visible = visible
            else:
                was_visible = self.part_visible.get(name, True)
                if was_visible and not visible:
                    outport_lookup = {}
                    for outport_info in part_info.get(name, []):
                        if outport_info.direction == "out":
                            outport_lookup[outport_info.value] = \
                                outport_info.type
                    self.sever_inports(child, outport_lookup)
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
                self.log_warning("Cannot restore non-existant attr %s" % k)
            else:
                assert "config" in attr.meta.tags, \
                    "Attr %s doesn't have config tag" % k
                if attr.value != v:
                    params[k] = v
        # Do this first so that any callbacks that happen in the put know
        # not to notify controller
        self.saved_structure = part_structure
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

    def sever_inports(self, child, outport_lookup=None):
        """Conditionally sever inport of the child. If outports is then None
        then sever all, otherwise restrict to the listed outports

        Args:
            child (Block): The child we are severing inports on
            outport_lookup (dict): {outport_value: outport_type} for each
                outport or None for all inports
        """
        attribute_values = {}
        for name, port_info in self._get_flowgraph_ports(child, "in").items():
            if outport_lookup is None or outport_lookup.get(
                    port_info.value, None) == port_info.type:
                attribute_values[name] = port_info.extra
        child.put_attribute_values(attribute_values)

    def child_connected(self, child, part_info):
        """Calculate if anything is connected to us or we are connected to
        anything else

        Args:
            child (Block): The child we are checking for connections on
            part_info (dict): {part_name: [PortInfo]} from other ports

        Returns:
            bool: True if we are connected or have nothing to connect
        """
        has_ports = False
        # See if our inports are connected to anything
        for inport_info in self._get_flowgraph_ports(child, "in").values():
            disconnected_value = inport_info.extra
            has_ports = True
            if inport_info.value != disconnected_value:
                return True
        # Calculate a lookup of outport values to their types
        # {outport_value: outport_type}
        outport_lookup = {}
        for outport_info in self._get_flowgraph_ports(child, "out").values():
            has_ports = True
            outport_lookup[outport_info.value] = outport_info.type
        # See if anything is connected to one of our outports
        for inport_info in PortInfo.filter_values(part_info):
            if outport_lookup.get(inport_info.value, None) == inport_info.type:
                return True
        # If we have ports and they haven't been connected to anything then
        # we are disconnected
        if has_ports:
            return False
        # otherwise, treat a block with no ports as connected
        else:
            return True
