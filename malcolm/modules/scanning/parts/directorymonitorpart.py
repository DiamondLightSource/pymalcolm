from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules.builtin.hooks import AContext
from malcolm.modules.builtin.parts import AMri, APartName, ChildPart

from .. import hooks

with Anno("Whether to raise a ValueError for a bad status"):
    AErrorOnFail = bool


class DirectoryMonitorPart(ChildPart):
    """Part for checking a directoryMonitor Manager is happy"""

    def __init__(
        self, name: APartName, mri: AMri, error_on_fail: AErrorOnFail = True
    ) -> None:
        super().__init__(name, mri, initial_visibility=True)
        self.error_on_fail = error_on_fail

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(hooks.ConfigureHook, self.check_directories)

    @add_call_types
    def check_directories(self, context: AContext) -> None:
        child = context.block_view(self.mri)
        try:
            child.managerCheck()
        except AssertionError:
            hostname = child.managerHostname.value
            bad_status_string = (
                f"{self.mri}: bad directory monitor status for server {hostname}"
            )
            self.log.error(bad_status_string)
            if self.error_on_fail:
                raise ValueError(bad_status_string)
