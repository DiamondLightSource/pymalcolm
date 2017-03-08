from malcolm.compat import OrderedDict
from malcolm.controllers.builtin.managercontroller import ManagerController, \
    LayoutInfo, PortInfo, ExportableInfo
from malcolm.core import Part, REQUIRED, method_also_takes, Attribute, \
    ResponseError, serialize_object, Task
from malcolm.vmetas.builtin import StringMeta

sm = ManagerController.stateMachine


@method_also_takes(
    "mri", StringMeta("Malcolm resource id of child object"), REQUIRED)
class ChildPart(Part):
    # Child block object
    child = None

    # {part_name: visible} saying whether part_name is visible
    part_visible = None

    # Layout options
    x = 0
    y = 0
    visible = None

    def store_params(self, params):
        super(ChildPart, self).store_params(params)
        self.child = self.process.get_block(params.mri)
        self.part_visible = {}

    @ManagerController.Disable
    def disable(self, task):
        if self.child["disable"].writeable:
            task.post(self.child["disable"])

    @ManagerController.Reset
    def reset(self, task):
        try:
            task.post(self.child["reset"])
        except ResponseError:
            # We get a "ValueError: child is not writeable" if we can't run
            # reset, probably because the child is already resetting,
            # so just wait for it to be idle
            task.when_matches(
                self.child["state"], sm.READY, bad_values=[sm.FAULT])

    @ManagerController.ReportPorts
    def report_ports(self, _):
        port_infos = list(self._get_flowgraph_ports("in").values())
        port_infos += list(self._get_flowgraph_ports("out").values())
        return port_infos

    @ManagerController.Layout
    def layout(self, task, part_info, layout_table):
        # if this is the first call, we need to calculate if we are visible
        # or not
        if self.visible is None:
            self.visible = self.child_connected(part_info)
        for i, name in enumerate(layout_table.name):
            _, _, x, y, visible = layout_table[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_inports(task)
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
                    self.sever_inports(task, outport_lookup)
                self.part_visible[name] = visible
        ret = LayoutInfo(
            mri=self.params.mri, x=self.x, y=self.y, visible=self.visible)
        return [ret]

    @ManagerController.Load
    def load(self, task, structure):
        part_structure = structure.get(self.name, {})
        futures = []
        for k, v in part_structure.items():
            try:
                attr = self.child[k]
            except KeyError:
                self.log_warning("Cannot restore non-existant attr %s" % k)
            else:
                if "config" not in attr.meta.tags:
                    raise ValueError("Attr %s doesn't have config tag" % k)
                futures += task.put_async(attr, v)
        task.wait_all(futures)

    @ManagerController.Save
    def save(self, task):
        part_structure = OrderedDict()
        for k in self.child:
            attr = self.child[k]
            if isinstance(attr, Attribute) and "config" in attr.meta.tags:
                part_structure[k] = serialize_object(attr.value)
        return part_structure

    @ManagerController.ReportExportable
    def report_exportable(self, task):
        ret = []
        for k in self.child:
            if k != "meta":
                attr = self.child[k]
                setter = self._make_setter(attr)
                ret.append(ExportableInfo(name=k, value=attr, setter=setter))
        return ret

    def _make_setter(self, attr):
        if isinstance(attr, Attribute):
            def setter(value):
                task = Task("ExportPutTask", self.process)
                task.put(attr, value)
        else:
            def setter(params=None):
                task = Task("ExportPostTask", self.process)
                task.post(attr, params)
        return setter

    def _get_flowgraph_ports(self, direction):
        """Get a PortInfo for each flowgraph of the child matching a direction

        Args:
            direction (str): Which direction to get, "in" or "out"

        Returns:
            dict: {Attribute: PortInfo}: PortInfo for the requested Attributes
        """
        ports = OrderedDict()
        for attr_name in self.child.endpoints:
            attr = self.child[attr_name]
            if isinstance(attr, Attribute):
                for tag in attr.meta.tags:
                    if tag.startswith("%sport" % direction):
                        direction, type, extra = tag.split(":", 3)
                        # Strip of the "port" suffix
                        direction = direction[:-4]
                        ports[attr] = PortInfo(direction=direction, type=type,
                                               value=attr.value, extra=extra)
        return ports

    def sever_inports(self, task, outport_lookup=None):
        """Conditionally sever inport of the child. If outports is then None
        then sever all, otherwise restrict to the listed outports

        Args:
            task (Task): The context to use to do the put()
            outport_lookup (dict): {outport_value: outport_type} for each
                outport or None for all inports
        """
        futures = []
        for attr, port_info in self._get_flowgraph_ports("in").items():
            if outport_lookup is None or outport_lookup.get(
                    port_info.value, None) == port_info.type:
                disconnected_value = port_info.extra
                futures += task.put_async(attr, disconnected_value)
        task.wait_all(futures)

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
        for inport_info in self._get_flowgraph_ports("in").values():
            disconnected_value = inport_info.extra
            has_ports = True
            if inport_info.value != disconnected_value:
                return True
        # Calculate a lookup of outport values to their types
        # {outport_value: outport_type}
        outport_lookup = {}
        for outport_info in self._get_flowgraph_ports("out").values():
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


