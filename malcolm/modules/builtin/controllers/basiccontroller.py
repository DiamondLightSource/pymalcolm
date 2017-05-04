from malcolm.core import Controller, method_takes, REQUIRED
from malcolm.modules.builtin.vmetas import StringMeta


@method_takes(
    "mri", StringMeta("Malcolm resource id of created block"), REQUIRED)
class BasicController(Controller):
    def __init__(self, process, parts, params):
        self.params = params
        super(BasicController, self).__init__(process, params.mri, parts)
