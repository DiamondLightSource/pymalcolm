from annotypes import Any

from ..controllers import ProxyController, AMri, AComms, \
    APublish


# This is done in python rather than YAML so that we can re-use Annos
def proxy_block(mri: AMri, comms: AComms, publish: APublish = False) -> Any:
    controller = ProxyController(mri, comms, publish)
    return [controller]
