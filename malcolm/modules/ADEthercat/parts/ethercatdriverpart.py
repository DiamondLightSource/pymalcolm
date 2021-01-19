from typing import Any

from annotypes import add_call_types

from malcolm.core import Context, DEFAULT_TIMEOUT, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning
from malcolm.modules.builtin.parts import AInitialVisibility, AStateful, ChildPart
from malcolm.modules.scanning.hooks import (
    AContext,
    PostRunArmedHook,
    PostRunReadyHook,
    PreRunHook,
)

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


@builtin.util.no_save("imageMode")
class EthercatDriverPart(ChildPart):
    def __init__(
        self,
        name: APartName,
        mri: AMri,
        initial_visibility: AInitialVisibility = False,
        stateful: AStateful = True,
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=stateful
        )
        self.min_exposure = 0.001

    def setup_driver(self, context: AContext) -> None:
        child = context.block_view(self.mri)

        # Check if we are acquiring
        if child.acquiring.value == True:
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
        self.setup_driver(context)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)

