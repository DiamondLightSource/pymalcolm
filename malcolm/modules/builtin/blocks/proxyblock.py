from malcolm.modules.builtin.controllers import ProxyController
from malcolm.core import method_takes, REQUIRED
from malcolm.modules.builtin.vmetas import StringMeta, BooleanMeta


# This is done in python rather than YAML so that we can choose whether or not
# to publish this block via the process
@method_takes(
    "comms", StringMeta("MRI for the comms block"), REQUIRED,
    "mri", StringMeta("MRI for the client block"), REQUIRED,
    "publish", BooleanMeta("Whether to publish this block"), False
)
def proxy_block(process, params):
    controller = ProxyController(process, (), params)
    process.add_controller(params.mri, controller, params.publish)
    return controller
