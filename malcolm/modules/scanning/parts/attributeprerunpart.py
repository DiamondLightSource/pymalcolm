from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin
from malcolm.modules.builtin.hooks import AContext

from .. import hooks

with Anno("Value to set during PreRunHook"):
    APreRunVal = str

with Anno("Value to set after a scan"):
    AResetVal = str

with Anno("Name of controlled attribute"):
    AAttrName = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class AttributePreRunPart(builtin.parts.ChildPart):
    """Part for controlling an attribute value during the PreRunHook"""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        pre_run_value: APreRunVal,
        reset_value: AResetVal,
        attribute_name: AAttrName = "shutter",
    ) -> None:
        super().__init__(name, mri, initial_visibility=True)
        self.pre_run_value = pre_run_value
        self.reset_value = reset_value
        self.attribute_name = attribute_name

        # We only want to set the attribute on configure
        no_save_attrs = set()
        no_save_attrs.add(self.attribute_name)
        existing = self.no_save_attribute_names or set()
        self.no_save_attribute_names = existing | no_save_attrs

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(hooks.PreRunHook, self.on_pre_run)
        registrar.hook(
            (hooks.PauseHook, hooks.AbortHook, hooks.PostRunReadyHook), self.on_reset
        )

    @add_call_types
    def on_pre_run(self, context: AContext) -> None:
        child = context.block_view(self.mri)
        getattr(child, self.attribute_name).put_value(self.pre_run_value)

    @add_call_types
    def on_reset(self, context: AContext) -> None:
        child = context.block_view(self.mri)
        getattr(child, self.attribute_name).put_value(self.reset_value)
