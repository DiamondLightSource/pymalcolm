from typing import Union

from annotypes import Anno, Array, add_call_types

from malcolm.core import CAMEL_RE, APartName, PartRegistrar
from malcolm.modules import builtin, scanning

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

with Anno("Single or list of valid multiples"):
    AMultiples = Union[Array[int]]


class MultipleTriggerPart(builtin.parts.ChildPart):
    """Part for informing a parent that it can have multiple
    triggers.
    """

    def __init__(
        self, name: APartName, mri: AMri, valid_multiples: AMultiples = None, initial_visibility: AInitialVisibility = False
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False
        )
        assert CAMEL_RE.match(name), (
            "MultipleTriggerPart name %r should be camelCase" % name
        )
        self.valid_multiples = valid_multiples

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
        # Check that PandA has frames_per_step of 2
        assert detectors, "No detectors found in table. Expecting a PandA"
        try:
            for i, mri in enumerate(detectors.mri):
                if mri == detector_mri:
                    assert detectors.framesPerStep[i] == 2, (
                        "Detector can only have framesPerStep=2"
                    )
        except AttributeError:
            raise
