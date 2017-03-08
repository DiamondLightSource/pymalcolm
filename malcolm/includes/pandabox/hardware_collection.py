from malcolm.core import method_takes, REQUIRED
from malcolm.vmetas.builtin import StringMeta, NumberMeta

from malcolm.parts.pandabox.pandaboxcontrol import PandABoxControl
from malcolm.parts.pandabox.pandaboxpoller import PandABoxPoller


@method_takes(
    "mriPrefix", StringMeta("Malcolm resource id prefix for blocks"), REQUIRED,
    "hostname", StringMeta("Hostname of the box"), "localhost",
    "port", NumberMeta("uint32", "Port number of the server control"), 8888,
    "areaDetectorPrefix",
        StringMeta("Prefix for areaDetector records, if using EPICS"), "")
def hardware_collection(process, params):

    # Connect to the Control port
    control = PandABoxControl(process, params.hostname, params.port)
    control.start()

    # Create a block updater
    poller = PandABoxPoller(process, control)

    # Get some information about what is available in this PandABox
    blocks_data = control.get_blocks_data()
    blocks = []
    parts = []

    for block_name, block_data in blocks_data.items():
        block_names = []
        if block_data.number == 1:
            block_names.append(block_name)
        else:
            for i in range(block_data.number):
                block_names.append("%s%d" % (block_name, i + 1))
        for bn in block_names:
            mri = "%s-%s" % (params.mriPrefix, bn)
            if block_name == "PCAP" and params.areaDetectorPrefix:
                extra_parts = make_pcap_ad_parts(
                    process, params.areaDetectorPrefix)
            else:
                extra_parts = []
            # Make a block
            block = poller.make_panda_block(
                mri, bn, block_data, extra_parts, params.areaDetectorPrefix)
            blocks.append(block)
            # Make it's corresponding part
            part = make_child_part(process, bn, mri, params.areaDetectorPrefix)
            parts.append(part)

    # Start polling
    poller.start()

    return blocks, parts


def make_pcap_ad_parts(process, prefix):
    from malcolm.includes.ADCore import adbase_parts
    params = adbase_parts.MethodMeta.prepare_input_map(prefix=prefix)
    _, ad_parts = adbase_parts(process, params)
    return ad_parts


def make_child_part(process, block_name, mri, prefix):
    if block_name == "PCAP" and prefix:
        from malcolm.parts.pandabox.pandaboxdriverpart import \
            PandABoxDriverPart as ChildPart
    elif prefix:
        from malcolm.parts.pandabox.pandaboxchildpart import \
            PandABoxChildPart as ChildPart
    else:
        from malcolm.parts.builtin.childpart import ChildPart

    params = ChildPart.MethodMeta.prepare_input_map(name=block_name, mri=mri)
    part = ChildPart(process, params)
    return part
