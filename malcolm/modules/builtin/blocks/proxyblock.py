from malcolm.controllers.builtin import ProxyController
from malcolm.core import method_takes, REQUIRED
from malcolm.modules.builtin.vmetas import StringMeta, BooleanMeta


@method_takes(
    "comms", StringMeta("MRI for the comms block"), REQUIRED,
    "mri", StringMeta("MRI for the client block"), REQUIRED,
    "publish", BooleanMeta("Whether to publish this block"), False
)
def proxy_block(process, params):
    controller = ProxyController(process, (), params)
    process.add_controller(params.mri, controller, params.publish)
    return controller
