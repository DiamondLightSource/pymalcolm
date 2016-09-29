from collections import OrderedDict

from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, NumberMeta

from malcolm.parts.pandabox.pandaboxcontrol import PandABoxControl
from malcolm.parts.pandabox.pandaboxpoller import PandABoxPoller
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.managercontroller import ManagerController


@method_takes(
    "name", StringMeta("Name of the created PandABox block"), REQUIRED,
    "hostname", StringMeta("Hostname of the box"), "localhost",
    "port", NumberMeta("uint32", "Port number of the server control"), 8888
)
def PandABox(process, params):

    # Connect to the Control port
    control = PandABoxControl(process, params.hostname, params.port)
    control.start()

    # Create a block updater
    poller = PandABoxPoller(process, control)

    # Get some information about what is available in this PandABox
    blocks_data = control.get_blocks_data()
    parts = OrderedDict()
    ret = []

    for block_name, block_data in blocks_data.items():
        block_names = []
        if block_data.number == 1:
            block_names.append(block_name)
        else:
            for i in range(block_data.number):
                block_names.append("%s%d" % (block_name, i+1))
        for bn in block_names:
            malcolm_name = "%s:%s" % (params.name, bn)
            ret.append(poller.make_panda_block(malcolm_name, bn, block_data))
            part_params = LayoutPart.MethodMeta.prepare_input_map(
                dict(name=bn, child=malcolm_name))
            parts[bn] = LayoutPart(process, part_params)

    # Make a controller
    controller = ManagerController(params.name, process, parts)
    ret.append(controller.block)

    # Start polling
    poller.start()

    return ret




