import os
import math
from xml.etree import cElementTree as ET

from annotypes import add_call_types, Anno, TYPE_CHECKING
from scanpointgenerator import CompoundGenerator, Dimension

from malcolm.compat import et_to_string
from malcolm.core import APartName, Future, Info, Block, PartRegistrar
from malcolm.modules import builtin, scanning
from ..infos import CalculatedNDAttributeDatasetInfo, DatasetType, \
    DatasetProducedInfo, NDArrayDatasetInfo, NDAttributeDatasetInfo, \
    AttributeDatasetType

if TYPE_CHECKING:
    from typing import Iterator, List, Dict

    PartInfo = Dict[str, List[Info]]

SUFFIXES = "NXY3456789"

# If the HDF writer doesn't get new frames in this time (seconds), consider it
# stalled and raise
FRAME_TIMEOUT = 60

with Anno("Directory to write data to"):
    AFileDir = str
with Anno("Argument for fileTemplate, normally filename without extension"):
    AFormatName = str
with Anno("""Printf style template to generate filename relative to fileDir.
Arguments are:
  1) %s: the value of formatName"""):
    AFileTemplate = str


def greater_than_zero(v):
    # type: (int) -> bool
    return v > 0


def create_dataset_infos(name, part_info, generator, filename):
    # type: (str, PartInfo, CompoundGenerator, str) -> Iterator[Info]
    # Update the dataset table
    uniqueid = "/entry/NDAttributes/NDArrayUniqueId"
    generator_rank = len(generator.dimensions)

    # Get the detector name from the primary source
    ndarray_infos = NDArrayDatasetInfo.filter_values(part_info)
    assert len(ndarray_infos) in (0, 1), \
        "More than one NDArrayDatasetInfo defined %s" % ndarray_infos

    # Add the primary datasource
    if ndarray_infos:
        ndarray_info = ndarray_infos[0]
        yield DatasetProducedInfo(
            name="%s.data" % name,
            filename=filename,
            type=DatasetType.PRIMARY,
            rank=ndarray_info.rank + generator_rank,
            path="/entry/detector/detector",
            uniqueid=uniqueid)

        # Add any secondary datasources
        for calculated_info in \
                CalculatedNDAttributeDatasetInfo.filter_values(part_info):
            yield DatasetProducedInfo(
                name="%s.%s" % (name, calculated_info.name),
                filename=filename,
                type=DatasetType.SECONDARY,
                rank=ndarray_info.rank + generator_rank,
                path="/entry/%s/%s" % (
                    calculated_info.name, calculated_info.name),
                uniqueid=uniqueid)

    # Add all the other datasources
    for dataset_info in NDAttributeDatasetInfo.filter_values(part_info):
        if dataset_info.type is AttributeDatasetType.DETECTOR:
            # Something like I0
            name = "%s.data" % dataset_info.name
            type = DatasetType.PRIMARY
        elif dataset_info.type is AttributeDatasetType.MONITOR:
            # Something like Iref
            name = "%s.data" % dataset_info.name
            type = DatasetType.MONITOR
        elif dataset_info.type is AttributeDatasetType.POSITION:
            # Something like x
            name = "%s.value" % dataset_info.name
            type = DatasetType.POSITION_VALUE
        else:
            raise AttributeError("Bad dataset type %r, should be a %s" % (
                dataset_info.type, AttributeDatasetType))
        yield DatasetProducedInfo(
            name=name,
            filename=filename,
            type=type,
            rank=dataset_info.rank + generator_rank,
            path="/entry/%s/%s" % (dataset_info.name, dataset_info.name),
            uniqueid=uniqueid)

    # Add any setpoint dimensions
    for dim in generator.axes:
        yield DatasetProducedInfo(
            name="%s.value_set" % dim,
            filename=filename,
            type=DatasetType.POSITION_SET,
            rank=1,
            path="/entry/detector/%s_set" % dim, uniqueid="")


def set_dimensions(child, generator):
    # type: (Block, CompoundGenerator) -> List[Future]
    num_dims = len(generator.dimensions)
    assert num_dims <= 10, \
        "Can only do 10 dims, you gave me %s" % num_dims
    attr_dict = dict(numExtraDims=num_dims - 1)
    # Fill in dim name and size
    # NOTE: HDF writer has these filled with fastest moving first
    # while dimensions is slowest moving first
    for i in range(10):
        suffix = SUFFIXES[i]
        if i < num_dims:
            forward_i = num_dims - i - 1
            index_name = "d%d" % forward_i
            index_size = generator.dimensions[forward_i].size
        else:
            index_name = ""
            index_size = 1
        attr_dict["posNameDim%s" % suffix] = index_name
        attr_dict["extraDimSize%s" % suffix] = index_size
    futures = child.put_attribute_values_async(attr_dict)
    return futures


def make_set_points(dimension, axis, data_el, units):
    # type: (Dimension, str, ET.Element, str) -> None
    axis_vals = ["%.12g" % p for p in dimension.get_positions(axis)]
    axis_el = ET.SubElement(
        data_el, "dataset", name="%s_set" % axis, source="constant",
        type="float", value=",".join(axis_vals))
    ET.SubElement(axis_el, "attribute", name="units", source="constant",
                  value=units, type="string")


def make_nxdata(name, rank, entry_el, generator, link=False):
    # type: (str, int, ET.Element, CompoundGenerator, bool) -> ET.Element
    # Make a dataset for the data
    data_el = ET.SubElement(entry_el, "group", name=name)
    ET.SubElement(data_el, "attribute", name="signal", source="constant",
                  value=name, type="string")
    pad_dims = []
    for d in generator.dimensions:
        if len(d.axes) == 1:
            pad_dims.append("%s_set" % d.axes[0])
        else:
            pad_dims.append(".")

    pad_dims += ["."] * rank
    ET.SubElement(data_el, "attribute", name="axes", source="constant",
                  value=",".join(pad_dims), type="string")
    ET.SubElement(data_el, "attribute", name="NX_class", source="constant",
                  value="NXdata", type="string")
    # Add in the indices into the dimensions array that our axes refer to
    for i, d in enumerate(generator.dimensions):
        for axis in d.axes:
            ET.SubElement(data_el, "attribute",
                          name="%s_set_indices" % axis,
                          source="constant", value=str(i), type="string")
            if link:
                ET.SubElement(data_el, "hardlink",
                              name="%s_set" % axis,
                              target="/entry/detector/%s_set" % axis)
            else:
                make_set_points(
                    d, axis, data_el, generator.units[axis])
    return data_el


def make_layout_xml(generator, part_info):
    # type: (CompoundGenerator, PartInfo) -> str
    # Make a root element with an NXEntry
    root_el = ET.Element("hdf5_layout")
    entry_el = ET.SubElement(root_el, "group", name="entry")
    ET.SubElement(entry_el, "attribute", name="NX_class",
                  source="constant", value="NXentry", type="string")

    # Check that there is only one primary source of detector data
    ndarray_infos = NDArrayDatasetInfo.filter_values(part_info)
    if not ndarray_infos:
        # Still need to put the data in the file, so manufacture something
        primary_rank = 1
    else:
        primary_rank = ndarray_infos[0].rank

    # Make an NXData element with the detector data in it in
    # /entry/detector/detector
    data_el = make_nxdata(
        "detector", primary_rank, entry_el, generator)
    det_el = ET.SubElement(data_el, "dataset", name="detector",
                           source="detector", det_default="true")
    ET.SubElement(det_el, "attribute", name="NX_class",
                  source="constant", value="SDS", type="string")

    # Now add any calculated sources of data
    for dataset_info in \
            CalculatedNDAttributeDatasetInfo.filter_values(part_info):
        # if we are a secondary source, use the same rank as the det
        attr_el = make_nxdata(
            dataset_info.name, primary_rank, entry_el, generator, link=True)
        ET.SubElement(attr_el, "dataset", name=dataset_info.name,
                      source="ndattribute", ndattribute=dataset_info.attr)

    # And then any other attribute sources of data
    for dataset_info in NDAttributeDatasetInfo.filter_values(part_info):
        # if we are a secondary source, use the same rank as the det
        attr_el = make_nxdata(dataset_info.name, dataset_info.rank,
                              entry_el, generator, link=True)
        ET.SubElement(attr_el, "dataset", name=dataset_info.name,
                      source="ndattribute", ndattribute=dataset_info.attr)

    # Add a group for attributes
    NDAttributes_el = ET.SubElement(entry_el, "group", name="NDAttributes",
                                    ndattr_default="true")
    ET.SubElement(NDAttributes_el, "attribute", name="NX_class",
                  source="constant", value="NXcollection", type="string")
    xml = et_to_string(root_el)
    return xml


class HDFWriterPart(builtin.parts.ChildPart):
    """Part for controlling an `hdf_writer_block` in a Device"""

    def __init__(self, name, mri):
        # type: (APartName, scanning.parts.AMri) -> None
        super(HDFWriterPart, self).__init__(name, mri)
        # Future for the start action
        self.start_future = None  # type: Future
        self.array_future = None  # type: Future
        self.done_when_reaches = 0
        # CompletedSteps = arrayCounter + self.uniqueid_offset
        self.uniqueid_offset = 0
        # The HDF5 layout file we write to say where the datasets go
        self.layout_filename = None  # type: str
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)
        self.register_hooked((scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.seek)
        self.register_hooked((scanning.hooks.RunHook,
                              scanning.hooks.ResumeHook), self.run)
        self.register_hooked(scanning.hooks.PostRunReadyHook,
                             self.post_run_ready)
        self.register_hooked(scanning.hooks.AbortHook, self.abort)

    @add_call_types
    def reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(HDFWriterPart, self).reset(context)
        self.abort(context)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(HDFWriterPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: AFileDir
                  formatName="det",  # type: AFormatName
                  fileTemplate="%s.h5",  # type: AFileTemplate
                  ):
        # type: (...) -> scanning.hooks.UInfos
        # On initial configure, expect to get the demanded number of frames
        self.done_when_reaches = completed_steps + steps_to_do
        self.uniqueid_offset = 0
        child = context.block_view(self.mri)
        # For first run then open the file
        # Enable position mode before setting any position related things
        child.positionMode.put_value(True)
        # Setup our required settings
        # TODO: this should be different for windows detectors
        file_dir = fileDir.rstrip(os.sep)
        filename = fileTemplate % formatName
        assert "." in filename, \
            "File extension for %r should be supplied" % filename
        futures = child.put_attribute_values_async(dict(
            enableCallbacks=True,
            fileWriteMode="Stream",
            swmrMode=True,
            positionMode=True,
            dimAttDatasets=True,
            lazyOpen=True,
            arrayCounter=0,
            filePath=file_dir + os.sep,
            fileName=formatName,
            fileTemplate="%s" + fileTemplate))
        futures += set_dimensions(child, generator)
        xml = make_layout_xml(generator, part_info)
        self.layout_filename = os.path.join(
            file_dir, "%s-layout.xml" % self.mri)
        with open(self.layout_filename, "w") as f:
            f.write(xml)
        # We want the HDF writer to flush this often:
        flush_time = 1  # seconds
        # (In particular this means that HDF files can be read cleanly by
        # SciSoft at the start of a scan.)
        assert generator.duration > 0, \
            "Duration %s for generator must be >0 to signify fixed exposure" \
            % generator.duration
        if generator.duration > flush_time:
            # We are going slower than 1/flush_time Hz, so flush every frame
            n_frames_between_flushes = 1
        else:
            # Limit update rate to be every flush_time seconds
            n_frames_between_flushes = int(math.ceil(
                flush_time / generator.duration))
            # But make sure we flush in this round of frames
            n_frames_between_flushes = min(
                steps_to_do, n_frames_between_flushes)
        futures += child.put_attribute_values_async(dict(
            xml=self.layout_filename,
            flushDataPerNFrames=n_frames_between_flushes,
            flushAttrPerNFrames=n_frames_between_flushes))
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Reset numCapture back to 0
        child.numCapture.put_value(0)
        # Start the plugin
        self.start_future = child.start_async()
        # Start a future waiting for the first array
        self.array_future = child.when_value_matches_async(
            "arrayCounterReadback", greater_than_zero)
        # Return the dataset information
        dataset_infos = list(create_dataset_infos(
            formatName, part_info, generator, filename))
        return dataset_infos

    @add_call_types
    def seek(self,
             context,  # type: scanning.hooks.AContext
             completed_steps,  # type: scanning.hooks.ACompletedSteps
             steps_to_do,  # type: scanning.hooks.AStepsToDo
             ):
        # type: (...) -> None
        # This is rewinding or setting up for another batch, so the detector
        # will skip to a uniqueID that has not been produced yet
        self.uniqueid_offset = completed_steps - self.done_when_reaches
        self.done_when_reaches += steps_to_do
        child = context.block_view(self.mri)
        # Just reset the array counter_block
        child.arrayCounter.put_value(0)
        # Start a future waiting for the first array
        self.array_future = child.when_value_matches_async(
            "arrayCounterReadback", greater_than_zero)

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        context.wait_all_futures(self.array_future)
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.uniqueId.subscribe_value(self.update_completed_steps)
        # TODO: what happens if we miss the last frame?
        child.when_value_matches(
            "uniqueId", self.done_when_reaches, event_timeout=FRAME_TIMEOUT)

    @add_call_types
    def post_run_ready(self, context):
        # type: (scanning.hooks.AContext) -> None
        # If this is the last one, wait until the file is closed
        context.wait_all_futures(self.start_future)
        # Delete the layout XML file
        os.remove(self.layout_filename)

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
        child.stop()

    def update_completed_steps(self, value):
        # type: (int) -> None
        completed_steps = value + self.uniqueid_offset
        self.registrar.report(scanning.infos.RunProgressInfo(completed_steps))
