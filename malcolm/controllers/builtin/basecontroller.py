from malcolm.core import Controller, method_takes, REQUIRED, Hook, Process
from malcolm.vmetas.builtin import StringMeta


@method_takes(
    "mri", StringMeta("Malcolm resource id of created block"), REQUIRED)
class BaseController(Controller):
    Init = Hook()
    """Called when this controller is told to start by the process

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    Halt = Hook()
    """Called when this controller is told to halt

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    def __init__(self, process, parts, params):
        self.params = params
        super(BaseController, self).__init__(process, params.mri, parts)

    @Process.Init
    def init(self):
        self.run_hook(self.Init, self.create_part_contexts())

    @Process.Halt
    def halt(self):
        self.run_hook(self.Halt, self.create_part_contexts())
