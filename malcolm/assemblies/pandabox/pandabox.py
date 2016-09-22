from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, NumberMeta

from malcolm.parts.pandabox.pandaboxcontrol import PandABoxControl

@method_takes(
    "hostname", StringMeta("Hostname of the box"), "localhost",
    "port", NumberMeta("uint8", "Port number of the server control"), 8888
)
def PandABox(process, params):
    control = PandABoxControl(process, params.hostname, params.port)
    control.start()

