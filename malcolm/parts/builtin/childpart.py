from malcolm.compat import OrderedDict
from malcolm.core import Part, REQUIRED, method_also_takes, Attribute, \
    ResponseError, serialize_object
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.managercontroller import ManagerController, \
    LayoutInfo, OutportInfo


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
    visible = False

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

    @ManagerController.ReportOutports
    def pre_layout(self, _):
        outports = self._get_flowgraph_ports("out")
        ret = []
        for port_tag in outports.values():
            _, type, value = port_tag.split(":", 3)
            ret.append(OutportInfo(type=type, value=value))
        return ret

    @ManagerController.Layout
    def layout(self, task, part_info, layout_table):
        for i, name in enumerate(layout_table.name):
            _, _, x, y, visible = layout_table[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_all_inports(task)
                self.x = x
                self.y = y
                self.visible = visible
            else:
                was_visible = self.part_visible.get(name, True)
                if was_visible and not visible:
                    outports = self.find_outports(name, part_info)
                    self.sever_inports_connected_to(task, outports)
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

    def _get_flowgraph_ports(self, direction="out"):
        # {attr_name: port_tag}
        ports = OrderedDict()
        for attr_name in self.child.endpoints:
            attr = self.child[attr_name]
            if isinstance(attr, Attribute):
                for tag in attr.meta.tags:
                    if tag.startswith("%sport" % direction):
                        ports[attr] = tag
        return ports

    def sever_all_inports(self, task):
        """Find all the inports of self.child, and disconnect them

        Args:
            task (Task): The task to use to do the put()
        """
        inports = self._get_flowgraph_ports("in")
        futures = []
        for attr, port_tag in inports.items():
            _, type, disconnected_value = port_tag.split(":", 3)
            futures += task.put_async(attr, disconnected_value)
        task.wait_all(futures)

    def find_outports(self, name, part_info):
        """Filter the part_outports dict with the name of a child part

        Args:
            name (str): Name of the Part
            part_info (dict): {name: [Info]}

        Returns:
            dict: {outport_value: outport_type}
        """
        outports = {}
        for outport_info in OutportInfo.filter_parts(part_info).get(name, []):
            outports[outport_info.value] = outport_info.type
        return outports

    def sever_inports_connected_to(self, task, outports):
        # Find the outports of this part
        # {outport_value: type} e.g. "PCOMP.OUT" -> "bit"
        inports = self._get_flowgraph_ports("in")
        futures = []
        for attr, port_tag in inports.items():
            _, type, disconnected_value = port_tag.split(":", 3)
            if outports.get(attr.value, None) == type:
                futures += task.put_async(attr, disconnected_value)
        task.wait_all(futures)
