# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types

from malcolm.core import APartName, PartRegistrar, CAMEL_RE
from malcolm.modules import builtin, scanning


# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility


class PandAAlternatingDivPart(builtin.parts.ChildPart):
    """Part for informing PandA that it can have multiple
    triggers.

    This part is used in beam selector scans (specific for K11
    DIAD beam line).
    """

    def __init__(self, name, mri, initial_visibility=None):
        # type: (APartName, AMri, AInitialVisibility) -> None
        super(PandAAlternatingDivPart, self).__init__(
            name,
            mri,
            initial_visibility=initial_visibility,
            stateful=False)
        assert CAMEL_RE.match(name), \
            "PandAAlternatingDivPart name %r should be camelCase" % name

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandAAlternatingDivPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook,
                       self.on_report_status)
        registrar.hook(scanning.hooks.ValidateHook,
                       self.on_validate)

    @add_call_types
    def on_report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        panda_mri = child.panda.value
        # Say that we can do multi frame for this detector
        info = scanning.infos.DetectorMutiframeInfo(panda_mri)
        return info

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_validate(self,
                    context, # type: scanning.hooks.AContext
                    detectors=None, # type: scanning.util.ADetectorTable
                    ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        panda_mri = child.panda.value
        # Check that PandA has frames_per_step of 2
        try:
            for i, mri in enumerate(detectors.mri):
                if mri == panda_mri:
                    assert detectors.framesPerStep[i] == 2, \
                      "PandA can only have framesPerStep=2 " \
                      "as it is alternating triggers between 2 detectors"
        except AttributeError:
            raise
