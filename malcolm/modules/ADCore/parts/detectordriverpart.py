from annotypes import Anno, add_call_types, Any, Array, Union, Sequence
from xml.etree import cElementTree as ET
from malcolm.compat import et_to_string
from malcolm.core import APartName, BadValueError, TableMeta, PartRegistrar, \
    config_tag
from malcolm.modules.builtin.parts import AMri, ChildPart
from malcolm.modules.builtin.util import no_save
from malcolm.modules.scanning.hooks import ReportStatusHook, \
    ConfigureHook, PostRunArmedHook, SeekHook, RunHook, ResumeHook, PauseHook, \
    AbortHook, AContext, UInfos, AStepsToDo, ACompletedSteps, APartInfo
from malcolm.modules.scanning.util import AGenerator
from ..infos import NDArrayDatasetInfo, NDAttributeDatasetInfo, \
    ExposureDeadtimeInfo, FilePathTranslatorInfo
from ..util import ADBaseActions, ExtraAttributesTable, \
    APartRunsOnWindows, DataType, SourceType
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
                 runs_on_windows=False,  # type: APartRunsOnWindows
                 ):
        # type: (...) -> None
        super(DetectorDriverPart, self).__init__(name, mri)
        self.soft_trigger_modes = soft_trigger_modes
        self.is_hardware_triggered = True
        self.main_dataset_useful = main_dataset_useful
        self.attributes_filename = ""
        self.actions = ADBaseActions(mri)
        self.extra_attributes = TableMeta.from_table(
            ExtraAttributesTable, "Extra attributes to be added to the dataset",
            writeable=(
                "name", "pv", "description", "sourceId", "sourceType",
                "dataType",
                "datasetType"),
            extra_tags=[config_tag()]
        ).create_attribute_model()
        self.runs_on_windows = runs_on_windows
        # Hooks
        self.register_hooked(ReportStatusHook, self.report_status)
        self.register_hooked((ConfigureHook, PostRunArmedHook, SeekHook),
                             self.configure, self.configure_args_with_exposure)
        self.register_hooked((RunHook, ResumeHook), self.run)
        self.register_hooked((PauseHook, AbortHook), self.abort)

    def build_attribute_xml(self):
        root_el = ET.Element("Attributes")
        for index, s_type in enumerate(self.extra_attributes.value.sourceType):
            if s_type == SourceType.PV:
                dbr_type = self.extra_attributes.value.dataType[index]
                if dbr_type == DataType.INT:
                    dbr_type = "DBR_LONG"
                elif dbr_type == DataType.DOUBLE:
                    dbr_type = "DBR_DOUBLE"
                elif dbr_type == DataType.STRING:
                    dbr_type = "DBR_STRING"
                else:
                    dbr_type = dbr_type.value
                ET.SubElement(
                    root_el, "Attribute",
                    name=self.extra_attributes.value.name[index],
                    type="EPICS_PV",
                    dbrtype=dbr_type,
                    description=self.extra_attributes.value.description[index],
                    source=self.extra_attributes.value.sourceId[index])
            elif s_type == SourceType.PARAM:
                ET.SubElement(
                    root_el, "Attribute",
                    name=self.extra_attributes.value.name[index],
                    type="PARAM",
                    datatype=self.extra_attributes.value.dataType[index].value,
                    description=self.extra_attributes.value.description[index],
                    source=self.extra_attributes.value.sourceId[index])
        return et_to_string(root_el)

    def set_extra_attributes(self, value):
        for row, _ in enumerate(value.name):
            if value.sourceType[row] == SourceType.PARAM:
                if value.dataType[row] == DataType.DBRNATIVE:
                    raise ValueError(
                        "data type DBR_NATIVE invalid for asyn param attribute")
        self.extra_attributes.set_value(value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(DetectorDriverPart, self).setup(registrar)
        registrar.add_attribute_model("attributesToCapture",
                                      self.extra_attributes,
                                      self.set_extra_attributes)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        super(DetectorDriverPart, self).reset(context)
        self.actions.abort_detector(context)
        # Delete the layout XML file
        if self.attributes_filename and os.path.isfile(
                self.attributes_filename):
            os.remove(self.attributes_filename)
            child = context.block_view(self.mri)
            child.attributesFile.put_value("")

    @add_call_types
    def report_status(self):
        # type: () -> UInfos
        ret = []
        if self.main_dataset_useful:
            ret.append(NDArrayDatasetInfo(rank=2))
        for name, dataset_type in zip(self.extra_attributes.value.name,
                                      self.extra_attributes.value.datasetType):
            ret.append(NDAttributeDatasetInfo(rank=2, name=name, attr=name,
                                              type=dataset_type))
        return ret

    def configure_args_with_exposure(self, keys):
        need_keys = self.configure.call_types.keys()
        if "exposure" in keys:
            need_keys.append("exposure")
        return need_keys

    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: AContext
                  completed_steps,  # type: ACompletedSteps
                  steps_to_do,  # type: AStepsToDo
                  part_info,  # type: APartInfo
                  generator,  # type: AGenerator
                  fileDir,  # type: AFileDir
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
            # Validate the exposure using the info provided
            kwargs["exposure"] = exposure_info.calculate_exposure(
                generator.duration, kwargs.get("exposure", 0.0))
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
        # Tell detector to store NDAttributes if table given
        if len(self.extra_attributes.value.sourceId) > 0:
            attribute_xml = self.build_attribute_xml()
            self.attributes_filename = os.path.join(
                fileDir, "%s-attributes.xml" % self.mri)
            with open(self.attributes_filename, 'w') as xml:
                xml.write(attribute_xml)
            assert hasattr(child, "attributesFile"), \
                "Block doesn't have 'attributesFile' attribute " \
                "(was it instantiated properly with adbase_parts?)"
            attributes_filename = self.attributes_filename
            if self.runs_on_windows:
                attributes_filename = \
                    FilePathTranslatorInfo.translate_filepath(
                     part_info, self.attributes_filename)
            child.attributesFile.put_value(attributes_filename)

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

