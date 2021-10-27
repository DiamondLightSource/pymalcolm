from annotypes import add_call_types

from malcolm.core import CAMEL_RE, APartName, PartRegistrar
from malcolm.modules import builtin, scanning

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility


class DoubleTriggerPart(builtin.parts.ChildPart):
    """Part for informing a parent that it can have 2 triggers per step."""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        initial_visibility: AInitialVisibility = False,
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False
        )
        assert CAMEL_RE.match(
            name
        ), f"DoubleTriggerPart name {name} should be camelCase"

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        registrar.hook(scanning.hooks.ValidateHook, self.on_validate)

    @add_call_types
    def on_report_status(
        self, context: scanning.hooks.AContext
    ) -> scanning.hooks.UInfos:
        child = context.block_view(self.mri)
        detector_mri = child.detector.value
        # Say that we can do multi frame for this detector
        info = scanning.infos.DetectorMutiframeInfo(detector_mri)
        return info

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_validate(
        self,
        context: scanning.hooks.AContext,
        detectors: scanning.util.ADetectorTable = None,
    ) -> None:
        child = context.block_view(self.mri)
        detector_mri = child.detector.value
        assert (
            detectors
        ), f"{detector_mri}: requires a detector table with 2 frames per step"
        if detectors:
            for enable, _, mri, _, frames in detectors.rows():
                if mri == detector_mri:
                    if enable and frames != 2:
                        raise ValueError(
                            f"{detector_mri}: frames per step has to be equal to 2"
                        )
