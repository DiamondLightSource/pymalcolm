from annotypes import Anno, add_call_types

from cothread import Sleep
from malcolm.core import APartName, PartRegistrar, DEFAULT_TIMEOUT
from malcolm.modules import builtin, scanning, ADOdin


# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

with Anno("eiger mri"):
    AEigerMri = str
with Anno("name of uid dataset"):
    AUidName = str
with Anno("name of sum dataset"):
    ASumName = str
with Anno("name of secondary dataset (e.g. sum)"):
    ASecondaryDataset = str

@builtin.util.no_save(
    "dataType",
)

class EigerOdinWriterPart(ADOdin.parts.OdinWriterPart):
    """Overrides standard OdinWriterPart to set datatype based on Eiger bit depth"""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        eiger_mri: AMri,
        initial_visibility: AInitialVisibility = True,
        uid_name: AUidName = "uid",
        sum_name: ASumName = "sum",
        secondary_set: ASecondaryDataset = "sum",
    ) -> None:
        self.eiger_mri = eiger_mri
        self.uid_name = uid_name
        self.sum_name = sum_name
        self.secondary_set = secondary_set
        super().__init__(name, mri, initial_visibility)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.report(scanning.hooks.ConfigureHook.create_info(self.on_configure))
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)

    @add_call_types
    def on_configure(
        self, 
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        generator: scanning.hooks.AGenerator,
        fileDir: scanning.hooks.AFileDir,
        formatName: scanning.hooks.AFormatName = "odin",
        fileTemplate: scanning.hooks.AFileTemplate = "%s.h5",
    ) -> None:
        
        child = context.block_view(self.mri)
        child_eiger = context.block_view(self.eiger_mri)
        # Don't wait for acquiring - instead we are interested in when eiger stale params PV goes to zero. 
        # Note this can fail if staleParameters goes true and then false before we get to this check. 
        child_eiger.when_value_matches("staleParameters", True, timeout=DEFAULT_TIMEOUT)
        child_eiger.when_value_matches("staleParameters", False, timeout=DEFAULT_TIMEOUT)

        # The above condition for acquiring going True is not currently enough to
        # guarantee that bitdepth has been updated.  Having to add Sleep for now.
        # Should be possible to modify ADEiger to avoid this.
        #Sleep(1.0)

        child.put_attribute_values(dict(dataType=f"UInt{child_eiger.bitdepth.value}"))
        super().on_configure(context, completed_steps, steps_to_do, generator, fileDir, formatName, fileTemplate)
