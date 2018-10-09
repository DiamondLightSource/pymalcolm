from annotypes import Any

from malcolm.modules.builtin.controllers import ProxyController, AMri, AComms, \
    APublish, AUseCothread


# This is done in python rather than YAML so that we can re-use Annos
def proxy_block(mri, comms, publish=False, use_cothread=False):
    # type: (AMri, AComms, APublish, AUseCothread) -> Any
    controller = ProxyController(mri, comms, publish, use_cothread)
    return [controller]
