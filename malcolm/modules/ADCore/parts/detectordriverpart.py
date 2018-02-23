from annotypes import Anno, add_call_types, Any

from malcolm.core import APartName, PartRegistrar, NumberMeta, Widget, \
    config_tag
from malcolm.modules.builtin.parts import AMri, ChildPart
from malcolm.modules.scanning.hooks import ReportStatusHook, ValidateHook, \
    ConfigureHook, PostRunArmedHook, SeekHook, RunHook, ResumeHook, PauseHook, \
    AbortHook, AContext, UInfos, AStepsToDo, ACompletedSteps
from malcolm.modules.scanning.util import AGenerator
from ..infos import NDArrayDatasetInfo
from ..util import ADBaseActions

with Anno("Is detector hardware triggered?"):
    AHardwareTriggered = bool
with Anno("Is main detector dataset useful to publish in DatasetTable?"):
    AMainDatasetUseful = bool
with Anno("If >0 then set exposure (s) from generator.duration - readoutTime"):
    AInitialReadoutTime = float


class DetectorDriverPart(ChildPart):
    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 is_hardware_triggered=True,  # type: AHardwareTriggered
                 main_dataset_useful=True,  # type: AMainDatasetUseful
                 initial_readout_time=-1.0,  # type: AInitialReadoutTime
                 ):
        # type: (...) -> None
        super(DetectorDriverPart, self).__init__(name, mri)
        self.is_hardware_triggered = is_hardware_triggered
        self.main_dataset_useful = main_dataset_useful
        self.actions = ADBaseActions(mri)
        # Attributes
        if initial_readout_time > 0:
            self.readout_time = NumberMeta(
                "float64", "Time taken to readout detector",
                tags=[Widget.TEXTINPUT.tag(), config_tag()]
            ).create_attribute_model(initial_readout_time)
        # Hooks
        self.register_hooked(ReportStatusHook, self.report_status)
        self.register_hooked(ValidateHook, self.validate)
        self.register_hooked((ConfigureHook, PostRunArmedHook, SeekHook),
                             self.configure)
        self.register_hooked((RunHook, ResumeHook), self.run)
        self.register_hooked((PauseHook, AbortHook), self.abort)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(DetectorDriverPart, self).setup(registrar)
        if hasattr(self, "readout_time"):
            registrar.add_attribute_model(
                "readoutTime", self.readout_time, self.readout_time.set_value)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        super(DetectorDriverPart, self).reset(context)
        self.actions.abort_detector(context)

    @add_call_types
    def report_status(self):
        # type: () -> UInfos
        if self.main_dataset_useful:
            return NDArrayDatasetInfo(rank=2)

    @add_call_types
    def validate(self, generator):
        # type: (AGenerator) -> None
        exposure = generator.duration
        assert exposure > 0, \
            "Duration %s for generator must be >0 to signify constant " \
            "exposure" % (exposure,)

        if hasattr(self, "readout_time"):
            exposure -= self.readout_time.value
            assert exposure > 0.0, \
                "Exposure time %s too small when readoutTime taken into " \
                "account" % (exposure,)

    @add_call_types
    def configure(self,
                  context,  # type: AContext
                  completed_steps,  # type: ACompletedSteps
                  steps_to_do,  # type: AStepsToDo
                  generator,  # type: AGenerator
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        if hasattr(self, "readout_time"):
            kwargs["exposure"] = generator.duration - self.readout_time.value
        self.actions.setup_detector(
            context, completed_steps, steps_to_do, **kwargs)
        if self.is_hardware_triggered:
            # Start now if we are hardware triggered
            self.actions.arm_detector(context)

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        if not self.is_hardware_triggered:
            # Start now if we are software triggered
            self.actions.arm_detector(context)
        self.actions.wait_for_detector(context, self.registrar)

    @add_call_types
    def abort(self, context):
        # type: (AContext) -> None
        self.actions.abort_detector(context)
