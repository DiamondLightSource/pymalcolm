from annotypes import add_call_types

from malcolm.core import DEFAULT_TIMEOUT, PartRegistrar
from malcolm.modules import builtin, scanning


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save(
    "enableCallbacks", "arrayCounter", "capture", "triggerMode", "averageSamples"
)
class ReframePluginPart(builtin.parts.ChildPart):
    """Part for controlling a 'reframe_plugin_block' in a Device"""

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(
            (
                scanning.hooks.ConfigureHook,
                scanning.hooks.PostRunArmedHook,
                scanning.hooks.SeekHook,
            ),
            self.on_configure,
        )
        registrar.hook(scanning.hooks.AbortHook, self.on_abort)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        part_info: scanning.hooks.APartInfo,
        fileDir: scanning.hooks.AFileDir,
    ) -> None:
        child = context.block_view(self.mri)
        fs = child.put_attribute_values_async(
            dict(
                arrayCounter=0,
                enableCallbacks=True,
                triggerMode="Continuous",
                averageSamples="Yes",
            )
        )
        context.wait_all_futures(fs)
        self.start_future = child.start_async()
        child.when_value_matches("acquireMode", "Armed", timeout=DEFAULT_TIMEOUT)

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext,) -> None:
        child = context.block_view(self.mri)
        child.stop()

    @add_call_types
    def on_reset(self, context: scanning.hooks.AContext) -> None:
        super().on_reset(context)
        child = context.block_view(self.mri)
        child.stop()
