from annotypes import Anno, add_call_types, Any, Array, Union, Sequence
from xml.etree import cElementTree as ET
from malcolm.compat import et_to_string
from malcolm.core import APartName, BadValueError, TableMeta, PartRegistrar, config_tag
from malcolm.modules.builtin.parts import AMri, ChildPart
from malcolm.modules.builtin.util import no_save
from malcolm.modules.scanning.hooks import ReportStatusHook, \
    ConfigureHook, PostRunArmedHook, SeekHook, RunHook, ResumeHook, PauseHook, \
    AbortHook, AContext, UInfos, AStepsToDo, ACompletedSteps, APartInfo
from malcolm.modules.scanning.util import AGenerator
from ..infos import NDArrayDatasetInfo, NDAttributeDatasetInfo, ExposureDeadtimeInfo
from ..util import ADBaseActions, PVSetTable, AttributeDatasetType
import os

with Anno("Is main detector dataset useful to publish in DatasetTable?"):
    AMainDatasetUseful = bool
with Anno("List of trigger modes that do not use hardware triggers"):
    ASoftTriggerModes = Array[str]
USoftTriggerModes = Union[ASoftTriggerModes, Sequence[str]]
with Anno("Directory to write data to"):
    AFileDir = str

# We will set these attributes on the child block, so don't save them
@no_save('arrayCounter', 'imageMode', 'numImages', 'arrayCallbacks', 'exposure',
         'acquirePeriod')
class DetectorDriverPart(ChildPart):
    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 soft_trigger_modes=None,  # type: USoftTriggerModes
                 main_dataset_useful=True,  # type: AMainDatasetUseful
                 ):
        # type: (...) -> None
        super(DetectorDriverPart, self).__init__(name, mri)
        self.soft_trigger_modes = soft_trigger_modes
        self.is_hardware_triggered = True
        self.main_dataset_useful = main_dataset_useful
        self.attributes_filename = ""
        self.actions = ADBaseActions(mri)
        self.pvsToCapture = TableMeta.from_table(
            PVSetTable, "PVs to be logged in HDF file", writeable=("name", "pv", "description")
        ).create_attribute_model()
        tags = list(self.pvsToCapture.meta.tags)
        tags.append(config_tag())
        self.pvsToCapture.meta.tags = tags
        self.pvsToCapture.set_meta(self.pvsToCapture.meta)
        # Hooks
        self.register_hooked(ReportStatusHook, self.report_status)
        self.register_hooked((ConfigureHook, PostRunArmedHook, SeekHook),
                             self.configure)
        self.register_hooked((RunHook, ResumeHook), self.run)
        self.register_hooked((PauseHook, AbortHook), self.abort)

    def build_attribute_xml(self):
        root_el = ET.Element("Attributes")
        for index in range(len(self.pvsToCapture.value.pv)):
            ET.SubElement(root_el, "Attribute", name=self.pvsToCapture.value.name[index], type="EPICS_PV",
                          dbrtype="DBR_DOUBLE", description=self.pvsToCapture.value.description[index],
                          source=self.pvsToCapture.value.pv[index])
        return et_to_string(root_el)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(DetectorDriverPart, self).setup(registrar)
        registrar.add_attribute_model("pvsToCapture", self.pvsToCapture, self.pvsToCapture.set_value)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        super(DetectorDriverPart, self).reset(context)
        self.actions.abort_detector(context)

    @add_call_types
    def report_status(self):
        # type: () -> UInfos
        ret = []
        if self.main_dataset_useful:
            ret.append(NDArrayDatasetInfo(rank=2))
        for attr in self.pvsToCapture.value.name:
            ret.append(NDAttributeDatasetInfo(rank=2, name="NDAttributes", attr=attr, type=AttributeDatasetType("monitor")))

        return ret

    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: AContext
                  completed_steps,  # type: ACompletedSteps
                  steps_to_do,  # type: AStepsToDo
                  part_info,  # type: APartInfo
                  generator,  # type: AGenerator
                  fileDir,   # type: AFileDir
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        try:
            exposure_info = ExposureDeadtimeInfo.filter_single_value(part_info)
        except BadValueError:
            # This is allowed, no exposure required
            exposure_info = None
        else:
            kwargs["exposure"] = exposure_info.calculate_exposure(
                generator.duration)
        self.actions.setup_detector(
            context, completed_steps, steps_to_do, **kwargs)
        # If detector can be soft triggered, then we might need to defer
        # starting it until run. Check triggerMode to find out
        if self.soft_trigger_modes:
            mode = child.triggerMode.value
            self.is_hardware_triggered = mode not in self.soft_trigger_modes
        # Might need to reset acquirePeriod as it's sometimes wrong
        # in some detectors
        if exposure_info:
            period = kwargs["exposure"] + exposure_info.readout_time
            child.acquirePeriod.put_value(period)
        if self.is_hardware_triggered:
            # Start now if we are hardware triggered
            self.actions.arm_detector(context)
        attribute_xml = self.build_attribute_xml()
        self.attributes_filename = os.path.join(
            fileDir, "%s-attributes.xml" % self.mri)
        with open(self.attributes_filename, 'w') as xml:
            xml.write(attribute_xml)
        futures = child.put_attribute_values_async(dict(
            attributesFile=self.attributes_filename))
        context.wait_all_futures(futures)

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

    @add_call_types
    def post_run_ready(self):
        # type: () -> None
        # Delete the attribute XML file
        os.remove(self.attributes_filename)
