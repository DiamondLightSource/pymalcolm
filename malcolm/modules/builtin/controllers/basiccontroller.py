from malcolm.core import Controller, method_takes, REQUIRED
from malcolm.modules.builtin.vmetas import StringMeta


@method_takes(
    "mri", StringMeta("Malcolm resource id of created block"), REQUIRED,
    "description", StringMeta("Description for the created block"), "")
class BasicController(Controller):
    """Basic Controller"""
    def __init__(self, process, parts, params):
        self.params = params
        super(BasicController, self).__init__(
            process, params.mri, parts, params.description)
