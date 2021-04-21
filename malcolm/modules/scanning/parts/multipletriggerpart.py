from typing import Sequence, Union

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
        self,
        name: APartName,
        mri: AMri,
        valid_multiples: Union[AMultiples, Sequence[int], int] = None,
        initial_visibility: AInitialVisibility = False,
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False
        )
        assert CAMEL_RE.match(name), (
            "MultipleTriggerPart name %r should be camelCase" % name
        )
        if valid_multiples:
            if isinstance(valid_multiples, int):
                self.valid_multiples = [valid_multiples]
            else:
                self.valid_multiples = list(valid_multiples)
        else:
            self.valid_multiples = list()

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

    def _check_frames_per_step_is_valid(self, detector_mri: str, frames_per_step: int) -> None:
        if frames_per_step <= 0:
            raise ValueError(f"{detector_mri}: frames per step has to be a positive value")
        if self.valid_multiples:
            if frames_per_step not in self.valid_multiples:
                raise ValueError(
                    f"{detector_mri}: frames per step {frames_per_step} "
                    f"not in set of valid values: {self.valid_multiples}"
                )

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
        if detectors:
            for enable, _, mri, _, frames in detectors.rows():
                if mri == detector_mri:
                    if enable:
                        self._check_frames_per_step_is_valid(detector_mri, frames)
                    return
        else:
            self._check_frames_per_step_is_valid(detector_mri, 1)
