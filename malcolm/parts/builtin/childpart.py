from collections import OrderedDict

from malcolm.core import Part, REQUIRED, method_takes, Attribute, Info
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.managercontroller import ManagerController, \
    LayoutInfo


class OutportInfo(Info):
    """Info about an outport and its value in a class

    Args:
        type (str): Type of the port, e.g. bit or NDArray
        value (str): Value that will be set when port is selected, e.g.
            PCOMP1.OUT or DET.STATS
    """
    def __init__(self, type, value):
        self.type = type
        self.value = value


sm = ManagerController.stateMachine


@method_takes(
    "name", StringMeta("Name of the part"), REQUIRED,
    "child", StringMeta("Name of child object"), REQUIRED)
class ChildPart(Part):
    # Child block object
    child = None

    # {part_name: visible} saying whether part_name is visible
    part_visible = None

    # Layout options
    x = 0
    y = 0
    visible = False
    mri = None
    name = None

    def store_params(self, params):
        super(ChildPart, self).store_params(params)
        self.child = self.process.get_block(params.child)
        self.name = params.name
        self.mri = params.child
        self.part_visible = {}

    @ManagerController.Disable
    def disable(self, task):
        task.post(self.child["disable"])

    @ManagerController.Reset
    def reset(self, task):
        # Wait until we have finished resetting
        if self.child.state == sm.RESETTING:
            task.when_matches(self.child["state"], sm.IDLE)
        else:
            # If we are in saving or editing then we can't do this, that's fine
            task.post(self.child["reset"])

    @ManagerController.ReportOutports
    def pre_layout(self, _):
        outports = self._get_flowgraph_ports("out")
        ret = []
        for port_tag in outports.values():
            _, _, type, value = port_tag.split(":", 4)
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
        ret = LayoutInfo(mri=self.mri, x=self.x, y=self.y, visible=self.visible)
        return ret

    def _get_flowgraph_ports(self, direction="out"):
        # {attr_name: port_tag}
        ports = OrderedDict()
        for attr_name in self.child.endpoints:
            attr = self.child[attr_name]
            if isinstance(attr, Attribute):
                for tag in attr.meta.tags:
                    if tag.startswith("flowgraph:%sport" % direction):
                        ports[attr] = tag
        return ports

    def sever_all_inports(self, task):
        """Find all the inports of self.child, and disconnect them

        Args:
            task (Task): The task to use to do the put()
        """
        inports = self._get_flowgraph_ports("in")
        futures = []
        for attr in inports:
            futures += task.put_async(attr, attr.meta.choices[0])
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
        for outport_info in OutportInfo.filter(part_info)[name]:
            outports[outport_info.value] = outport_info.type
        return outports

    def sever_inports_connected_to(self, task, outports):
        # Find the outports of this part
        # {outport_value: type} e.g. "PCOMP.OUT" -> "bit"
        inports = self._get_flowgraph_ports("in")
        futures = []
        for attr, port_tag in inports.items():
            typ = port_tag.split(":")[2]
            if outports.get(attr.value, None) == typ:
                futures += task.put_async(attr, attr.meta.choices[0])
        task.wait_all(futures)
