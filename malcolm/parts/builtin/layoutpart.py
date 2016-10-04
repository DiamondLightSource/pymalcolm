from collections import OrderedDict

from malcolm.core import Part, REQUIRED, method_takes, method_returns, Attribute
from malcolm.core.vmetas import StringMeta, NumberMeta, BooleanMeta, \
    StringArrayMeta
from malcolm.controllers.managercontroller import ManagerController, \
    layout_table_meta, outport_table_meta


@method_takes(
    "name", StringMeta("Name of the part"), REQUIRED,
    "child", StringMeta("Name of child object"), REQUIRED)
class LayoutPart(Part):
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
        super(LayoutPart, self).store_params(params)
        self.child = self.process.get_block(params.child)
        self.name = params.name
        self.mri = params.child
        self.part_visible = {}

    @ManagerController.ListOutports
    @method_returns(
        "type", StringArrayMeta("Type of outport (e.g. bit or pos)"), REQUIRED,
        "value", StringArrayMeta(
            "Value of outport (e.g. PULSE1.OUT)"), REQUIRED)
    def list_outports(self, _, returns):
        outports = self._get_flowgraph_ports("out")
        types = []
        values = []
        for port_tag in outports.values():
            _, _, typ, name = port_tag.split(":", 4)
            types.append(typ)
            values.append(name)
        returns.type = types
        returns.value = values
        return returns

    @ManagerController.UpdateLayout
    @method_takes(
        "layout_table", layout_table_meta, REQUIRED,
        "outport_table", outport_table_meta, REQUIRED
    )
    @method_returns(
        "mri", StringMeta("Malcolm full name of child block"), REQUIRED,
        "x", NumberMeta("float64", "X Co-ordinate of child block"), REQUIRED,
        "y", NumberMeta("float64", "X Co-ordinate of child block"), REQUIRED,
        "visible", BooleanMeta("Whether child block is visible"), REQUIRED)
    def update_layout_table(self, task, params, returns):
        for i, name in enumerate(params.layout_table.name):
            _, _, x, y, visible = params.layout_table[i]
            if name == self.name:
                if self.visible and not visible:
                    self.sever_all_inports(task)
                self.x = x
                self.y = y
                self.visible = visible
            else:
                was_visible = self.part_visible.get(name, True)
                if was_visible and not visible:
                    outports = self.find_outports(name, params.outport_table)
                    self.sever_inports_connected_to(task, outports)
                self.part_visible[name] = visible
        returns.mri = self.mri
        returns.x = self.x
        returns.y = self.y
        returns.visible = self.visible
        return returns

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

    def find_outports(self, name, outport_table):
        """Filter the outport_table with the name of a child part

        Args:
            name (str): Name of the Part
            outport_table (Table): Table of name, value, type

        Returns:
            dict: {outport_value: outport_type}
        """
        outports = {}
        for i, n in enumerate(outport_table.name):
            if n == name:
                outports[outport_table.value[i]] = outport_table.type[i]
        return outports

    def sever_inports_connected_to(self, task, outports):
        # Find the outports of this part
        # {outport_value: typ} e.g. "PCOMP.OUT" -> "bit"
        inports = self._get_flowgraph_ports("in")
        futures = []
        for attr, port_tag in inports.items():
            typ = port_tag.split(":")[2]
            if outports.get(attr.value, None) == typ:
                futures += task.put_async(attr, attr.meta.choices[0])
        task.wait_all(futures)
