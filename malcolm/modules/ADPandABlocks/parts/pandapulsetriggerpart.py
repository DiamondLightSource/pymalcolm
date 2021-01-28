from typing import Optional

from annotypes import add_call_types

from malcolm.core import CAMEL_RE, APartName, BadValueError, PartRegistrar
from malcolm.modules import builtin, scanning

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility


class PandAPulseTriggerPart(builtin.parts.ChildPart):
    """Part for operating a single PULSE block in a PandA to stretch a trigger
    pulse into a gate centred on the middle of the exposure. For the PandA it
    needs the following exports:

    - $(name)Width: width Attribute of the PULSE block with units set to "s"
    - $(name)Delay: delay Attribute of the PULSE block with units set to "s"
    - $(name)Step: step Attribute of the PULSE block with units set to "s"
    - $(name)Pulses: pulses Attribute of the PULSE block

    The Detector is required to have:
    - exposure: an Attribute that reports after configure() the exposure that
      is expected by the detector
    """

    def __init__(
        self, name: APartName, mri: AMri, initial_visibility: AInitialVisibility = True
    ) -> None:
        super().__init__(
            name, mri, initial_visibility=initial_visibility, stateful=False
        )
        assert CAMEL_RE.match(name), (
            "PandAPulseTriggerPart name %r should be camelCase" % name
        )
        # The stored generator duration and detector framesPerStep from
        # configure
        self.generator_duration = None
        self.frames_per_step = 1
        # The panda Block we will be prodding
        self.panda = None
        # The detector Block we will be reading from
        self.detector = None

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)
        registrar.hook(scanning.hooks.PostConfigureHook, self.on_post_configure)

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
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        generator: scanning.hooks.AGenerator,
        detectors: scanning.util.ADetectorTable = None,
    ) -> None:
        assert generator.duration > 0, (
            "Can only create pulse triggers for a generator with the same "
            "duration for every point, not %s" % generator
        )
        self.generator_duration = generator.duration

        # Get the panda and the detector we will be using
        child = context.block_view(self.mri)
        panda_mri = child.panda.value
        self.panda = context.block_view(panda_mri)
        detector_mri = child.detector.value
        self.detector = context.block_view(detector_mri)

        # Get the framesPerStep for this detector from the detectors table
        assert detectors, "No detectors passed in table"
        for enable, _, mri, _, frames_per_step in detectors.rows():
            if mri == detector_mri:
                # Found a row telling us how many frames per step to generate
                if enable:
                    assert (
                        frames_per_step > 0
                    ), "Zero frames per step for %s, how did this happen?" % (mri)
                    self.frames_per_step = frames_per_step
                else:
                    self.frames_per_step = 0
                break
        else:
            raise BadValueError(
                "Detector table %s doesn't contain row for %s"
                % (detectors, detector_mri)
            )

        # Check that the Attributes we expect are exported
        pulse_name = None
        suffixes = ["Pulses", "Width", "Step", "Delay"]
        expected_exports = set(self.name + s for s in suffixes)
        assert self.panda, "No assigned PandA"
        for source, export in self.panda.exports.value.rows():
            if export in expected_exports:
                part_name = source.split(".")[0]
                if pulse_name:
                    assert part_name == pulse_name, (
                        "Export %s defined for a different pulse block" % export
                    )
                else:
                    pulse_name = part_name
                expected_exports.remove(export)
        assert not expected_exports, "PandA %r did not define exports %s" % (
            panda_mri,
            sorted(expected_exports),
        )

        # Find the PULSE Block for further checks
        pulse_mri: Optional[str] = None
        assert self.panda, "No assigned PandA"
        for name, mri, _, _, _ in self.panda.layout.value.rows():
            if name == pulse_name:
                pulse_mri = mri
        assert pulse_mri, "Can't find mri for pulse block %r" % pulse_name

        # Check that the Attributes have the right units for all except Pulses
        pulse_block = context.block_view(pulse_mri)
        for suffix in suffixes:
            if suffix != "Pulses":
                units = pulse_block[suffix.lower() + "Units"].value
                assert (
                    units == "s"
                ), "Pulse block %r attribute %r needs units 's', not %r" % (
                    panda_mri,
                    suffix,
                    units,
                )

    def on_post_configure(self):
        if self.frames_per_step > 0:
            # Sanity check that the detector is armed
            detector_state = self.detector.state.value
            assert (
                detector_state == "Armed"
            ), "Expected %s to be Armed, but it is %s" % (
                self.detector.mri,
                detector_state,
            )
            # We are taking part, so calculate pulse values
            step = float(self.generator_duration) / self.frames_per_step
            try:
                width = self.detector.exposure.value
            except KeyError:
                # No exposure, so assume a very tiny readout time
                width = step - 1e-6
            assert width < step, "Width %s is not less than Step %s" % (width, step)
            values = {
                self.name + "Step": step,
                self.name + "Width": width,
                self.name + "Delay": (step - width) / 2,
                self.name + "Pulses": self.frames_per_step,
            }
            self.panda.put_attribute_values(values)
