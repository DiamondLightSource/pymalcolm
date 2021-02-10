from annotypes import add_call_types

from malcolm.core import DEFAULT_TIMEOUT, PartRegistrar
from malcolm.modules import builtin, scanning
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.scanning.hooks import AContext

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


@builtin.util.no_save("imageMode")
class EthercatDriverPart(ChildPart):
    def _setup_driver(self, context: AContext) -> None:
        child = context.block_view(self.mri)

        # Check if we are acquiring
        if child.acquiring.value is True:
            # Check image mode is correct
            if child.imageMode.value == "Continuous":
                return
            # Stop if in wrong mode
            else:
                child.stop_async()
                child.when_value_matches("acquiring", False, timeout=DEFAULT_TIMEOUT)

        # Just run the driver in continuous mode
        child.imageMode.put_value("Continuous")
        child.start_async()
        child.when_value_matches("acquiring", True, timeout=DEFAULT_TIMEOUT)

    @add_call_types
    def on_configure(self, context: AContext) -> None:
        self._setup_driver(context)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)
