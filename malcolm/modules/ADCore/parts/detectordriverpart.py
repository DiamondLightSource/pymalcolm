import os
from xml.etree import cElementTree as ET

from annotypes import Anno, add_call_types, Any, Array, Union, Sequence
from typing import Optional

from malcolm.compat import et_to_string
from malcolm.core import APartName, BadValueError, TableMeta, PartRegistrar, \
    config_tag, Future, Context, DEFAULT_TIMEOUT
from malcolm.modules import builtin, scanning
from ..infos import NDArrayDatasetInfo, NDAttributeDatasetInfo, \
    FilePathTranslatorInfo
from ..util import ExtraAttributesTable, APartRunsOnWindows, DataType, \
    SourceType, FRAME_TIMEOUT

with Anno("Is main detector dataset useful to publish in DatasetTable?"):
    AMainDatasetUseful = bool
with Anno("List of trigger modes that do not use hardware triggers"):
    ASoftTriggerModes = Array[str]
USoftTriggerModes = Union[ASoftTriggerModes, Sequence[str]]

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save('arrayCounter', 'imageMode', 'numImages',
                      'arrayCallbacks', 'exposure', 'acquirePeriod')
class DetectorDriverPart(builtin.parts.ChildPart):
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
        self.extra_attributes = TableMeta.from_table(
            ExtraAttributesTable, "Extra attributes to be added to the dataset",
            writeable=(
                "name", "pv", "description", "sourceId", "sourceType",
                "dataType",
                "datasetType"),
            extra_tags=[config_tag()]
        ).create_attribute_model()
        self.runs_on_windows = runs_on_windows
        # How long to wait between frame updates before error
        self.frame_timeout = 0.0
        # When arrayCounter gets to here we are done
        self.done_when_reaches = 0
        # CompletedSteps = arrayCounter + self.uniqueid_offset
        self.uniqueid_offset = 0
        # A future that completes when detector start calls back
        self.start_future = None  # type: Future

    def setup_detector(self,
                       context,  # type: Context
                       completed_steps,  # type: scanning.hooks.ACompletedSteps
                       steps_to_do,  # type: scanning.hooks.AStepsToDo
                       duration,  # type: float
                       part_info,  # type: scanning.hooks.APartInfo
                       **kwargs  # type: Any
                       ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        if completed_steps == 0:
            # This is an initial configure, so reset arrayCounter to 0
            array_counter = 0
            self.done_when_reaches = steps_to_do
        else:
            # This is rewinding or setting up for another batch,
            # skip to a uniqueID that has not been produced yet
            array_counter = self.done_when_reaches
            self.done_when_reaches += steps_to_do
        self.uniqueid_offset = completed_steps - array_counter
        for k, v in dict(
                arrayCounter=array_counter,
                imageMode="Multiple",
                numImages=steps_to_do,
                arrayCallbacks=True).items():
            if k not in kwargs and k in child:
                kwargs[k] = v
        child.put_attribute_values(kwargs)
        # Might need to reset acquirePeriod as it's sometimes wrong
        # in some detectors
        try:
            info = scanning.infos.ExposureDeadtimeInfo.filter_single_value(
                part_info)
        except BadValueError:
            # This is ok, no exposure info
            pass
        else:
            exposure = kwargs.get("exposure", info.calculate_exposure(duration))
            child.acquirePeriod.put_value(exposure + info.readout_time)

    def arm_detector(self, context):
        # type: (Context) -> None
        child = context.block_view(self.mri)
        self.start_future = child.start_async()
        child.when_value_matches("acquiring", True, timeout=DEFAULT_TIMEOUT)

    def wait_for_detector(self, context, registrar, event_timeout=None):
        # type: (Context, PartRegistrar, Optional[float]) -> None
        child = context.block_view(self.mri)
        child.arrayCounterReadback.subscribe_value(
            self.update_completed_steps, registrar)
        # If no new frames produced in event_timeout seconds, consider scan dead
        context.wait_all_futures(self.start_future, event_timeout=event_timeout)
        # Now wait to make sure any update_completed_steps come in. Give
        # it 5 seconds to timeout just in case there are any stray frames that
        # haven't made it through yet
        child.when_value_matches(
            "arrayCounterReadback", self.done_when_reaches,
            timeout=DEFAULT_TIMEOUT)

    def abort_detector(self, context):
        # type: (Context) -> None
        child = context.block_view(self.mri)
        child.stop()
        # Stop is a put to a busy record which returns immediately
        # The detector might take a while to actually stop so use the
        # acquiring pv (which is the same asyn parameter as the busy record
        # that stop() pokes) to check that it has finished
        child.when_value_matches("acquiring", False, timeout=DEFAULT_TIMEOUT)

    def update_completed_steps(self, value, registrar):
        # type: (int, PartRegistrar) -> None
        completed_steps = value + self.uniqueid_offset
        registrar.report(scanning.infos.RunProgressInfo(completed_steps))

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
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        registrar.hook((scanning.hooks.ConfigureHook,
                        scanning.hooks.PostRunArmedHook,
                        scanning.hooks.SeekHook),
                       self.on_configure, self.configure_args_with_exposure)
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(
            (scanning.hooks.PauseHook, scanning.hooks.AbortHook), self.on_abort)
        # Attributes
        registrar.add_attribute_model("attributesToCapture",
                                      self.extra_attributes,
                                      self.set_extra_attributes)

    @add_call_types
    def on_reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(DetectorDriverPart, self).on_reset(context)
        self.abort_detector(context)
        # Delete the layout XML file
        if self.attributes_filename and os.path.isfile(
                self.attributes_filename):
            os.remove(self.attributes_filename)
            child = context.block_view(self.mri)
            child.attributesFile.put_value("")

    @add_call_types
    def on_report_status(self):
        # type: () -> scanning.hooks.UInfos
        ret = []
        if self.main_dataset_useful:
            ret.append(NDArrayDatasetInfo(rank=2))
        for name, dataset_type in zip(self.extra_attributes.value.name,
                                      self.extra_attributes.value.datasetType):
            ret.append(NDAttributeDatasetInfo.from_attribute_type(
                name=name, attr=name, type=dataset_type))
        return ret

    def configure_args_with_exposure(self, keys):
        need_keys = self.on_configure.call_types.keys()
        if "exposure" in keys:
            need_keys.append("exposure")
        return need_keys

    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(self,
                     context,  # type: scanning.hooks.AContext
                     completed_steps,  # type: scanning.hooks.ACompletedSteps
                     steps_to_do,  # type: scanning.hooks.AStepsToDo
                     part_info,  # type: scanning.hooks.APartInfo
                     generator,  # type: scanning.hooks.AGenerator
                     fileDir,  # type: scanning.hooks.AFileDir
                     **kwargs  # type: Any
                     ):
        # type: (...) -> None
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        self.setup_detector(context, completed_steps, steps_to_do,
                            generator.duration, part_info, **kwargs)
        # Calculate how long to wait before marking this scan as stalled
        self.frame_timeout = FRAME_TIMEOUT
        if generator.duration > 0:
            self.frame_timeout += generator.duration
        else:
            # Double it to be safe
            self.frame_timeout += FRAME_TIMEOUT
        # If detector can be soft triggered, then we might need to defer
        # starting it until run. Check triggerMode to find out
        if self.soft_trigger_modes:
            mode = child.triggerMode.value
            self.is_hardware_triggered = mode not in self.soft_trigger_modes
        if self.is_hardware_triggered:
            # Start now if we are hardware triggered
            self.arm_detector(context)
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
    def on_run(self, context):
        # type: (scanning.hooks.AContext) -> None
        if not self.is_hardware_triggered:
            # Start now if we are software triggered
            self.arm_detector(context)
        self.wait_for_detector(
            context, self.registrar, event_timeout=self.frame_timeout)

    @add_call_types
    def on_abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        self.abort_detector(context)
