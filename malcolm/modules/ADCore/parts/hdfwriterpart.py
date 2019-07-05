import os
import time
from xml.etree import cElementTree as ET

from annotypes import Anno, add_call_types, TYPE_CHECKING
from scanpointgenerator import CompoundGenerator, Dimension

from malcolm.compat import et_to_string
from malcolm.core import APartName, Future, Info, Block, PartRegistrar, \
    BooleanMeta, Widget, config_tag, TimeoutError
from malcolm.modules import builtin, scanning
from ..infos import CalculatedNDAttributeDatasetInfo, NDArrayDatasetInfo, \
    NDAttributeDatasetInfo, \
    AttributeDatasetType, FilePathTranslatorInfo
from ..util import APartRunsOnWindows

if TYPE_CHECKING:
    from typing import Iterator, List, Dict

    PartInfo = Dict[str, List[Info]]

SUFFIXES = "NXY3456789"

# If the HDF writer doesn't get new frames in this time (seconds), consider it
# stalled and raise
FRAME_TIMEOUT = 60

with Anno("Toggle writing of all ND attributes to HDF file"):
    AWriteAllNDAttributes = bool

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
APartRunsOnWindows = APartRunsOnWindows


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
        yield scanning.infos.DatasetProducedInfo(
            name="%s.data" % name,
            filename=filename,
            type=scanning.util.DatasetType.PRIMARY,
            rank=ndarray_info.rank + generator_rank,
            path="/entry/detector/detector",
            uniqueid=uniqueid)

        # Add any secondary datasources
        for calculated_info in \
                CalculatedNDAttributeDatasetInfo.filter_values(part_info):
            yield scanning.infos.DatasetProducedInfo(
                name="%s.%s" % (name, calculated_info.name),
                filename=filename,
                type=scanning.util.DatasetType.SECONDARY,
                rank=ndarray_info.rank + generator_rank,
                path="/entry/%s/%s" % (
                    calculated_info.name, calculated_info.name),
                uniqueid=uniqueid)

    # Add all the other datasources
    for dataset_info in NDAttributeDatasetInfo.filter_values(part_info):
        if dataset_info.type is AttributeDatasetType.DETECTOR:
            # Something like I0
            name = "%s.data" % dataset_info.name
            dtype = scanning.util.DatasetType.PRIMARY
        elif dataset_info.type is AttributeDatasetType.MONITOR:
            # Something like Iref
            name = "%s.data" % dataset_info.name
            dtype = scanning.util.DatasetType.MONITOR
        elif dataset_info.type is AttributeDatasetType.POSITION:
            # Something like x
            name = "%s.value" % dataset_info.name
            dtype = scanning.util.DatasetType.POSITION_VALUE
        else:
            raise AttributeError("Bad dataset type %r, should be a %s" % (
                dataset_info.type, AttributeDatasetType))
        yield scanning.infos.DatasetProducedInfo(
            name=name,
            filename=filename,
            type=dtype,
            rank=dataset_info.rank + generator_rank,
            path="/entry/%s/%s" % (dataset_info.name, dataset_info.name),
            uniqueid=uniqueid)

    # Add any setpoint dimensions
    for dim in generator.axes:
        yield scanning.infos.DatasetProducedInfo(
            name="%s.value_set" % dim,
            filename=filename,
            type=scanning.util.DatasetType.POSITION_SET,
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


def make_layout_xml(generator, part_info, write_all_nd_attributes=False):
    # type: (CompoundGenerator, PartInfo, bool) -> str
    # Make a root element with an NXEntry
    root_el = ET.Element("hdf5_layout", auto_ndattr_default="false")
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
    ndattr_default = "true" if write_all_nd_attributes else "false"
    nd_attributes_el = ET.SubElement(entry_el, "group", name="NDAttributes",
                                     ndattr_default=ndattr_default)
    ET.SubElement(nd_attributes_el, "attribute", name="NX_class",
                  source="constant", value="NXcollection", type="string")
    ET.SubElement(nd_attributes_el, "dataset", name="NDArrayUniqueId",
                  source="ndattribute", ndattribute="NDArrayUniqueId")
    ET.SubElement(nd_attributes_el, "dataset", name="NDArrayTimeStamp",
                  source="ndattribute", ndattribute="NDArrayTimeStamp")

    xml = et_to_string(root_el)
    return xml


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save(
    'positionMode', 'enableCallbacks', 'fileWriteMode', 'swmrMode', 'storeAttr',
    'dimAttDatasets', 'lazyOpen', 'arrayCounter', 'filePath', 'fileName',
    'fileTemplate', 'numExtraDims', 'flushAttrPerNFrames', 'xmlLayout',
    'flushDataPerNFrames', 'numCapture')
@builtin.util.no_save("posNameDim%s" % SUFFIXES[i] for i in range(10))
@builtin.util.no_save("extraDimSize%s" % SUFFIXES[i] for i in range(10))
class HDFWriterPart(builtin.parts.ChildPart):
    """Part for controlling an `hdf_writer_block` in a Device"""

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 runs_on_windows=False,  # type: APartRunsOnWindows
                 write_all_nd_attributes=True,  # type: AWriteAllNDAttributes
                 ):
        # type: (...) -> None
        super(HDFWriterPart, self).__init__(name, mri)
        # Future for the start action
        self.start_future = None  # type: Future
        self.array_future = None  # type: Future
        self.done_when_reaches = 0
        # This is when uniqueId last updated
        self.last_id_update = None
        # CompletedSteps = arrayCounter + self.uniqueid_offset
        self.uniqueid_offset = 0
        # The HDF5 layout file we write to say where the datasets go
        self.layout_filename = None  # type: str
        self.runs_on_windows = runs_on_windows
        # How long to wait between frame updates before error
        self.frame_timeout = 0.0
        self.write_all_nd_attributes = BooleanMeta(
            "Toggles whether all NDAttributes are written to "
            "file, or only those specified in the dataset",
            writeable=True,
            tags=[Widget.CHECKBOX.tag(), config_tag()]).create_attribute_model(
            write_all_nd_attributes)

    @add_call_types
    def reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(HDFWriterPart, self).reset(context)
        self.abort(context)
        # HDFWriter might have still be writing so stop doesn't guarantee
        # flushed all frames start_future is in a different context so
        # can't wait for it, so just wait for the running attribute to be false
        child = context.block_view(self.mri)
        child.when_value_matches("running", False)
        # Delete the layout XML file
        if self.layout_filename and os.path.isfile(self.layout_filename):
            os.remove(self.layout_filename)
            child.xmlLayout.put_value("")

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(HDFWriterPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.configure)
        registrar.hook((scanning.hooks.PostRunArmedHook,
                        scanning.hooks.SeekHook), self.seek)
        registrar.hook((scanning.hooks.RunHook,
                        scanning.hooks.ResumeHook), self.run)
        registrar.hook(scanning.hooks.PostRunReadyHook, self.post_run_ready)
        registrar.hook(scanning.hooks.AbortHook, self.abort)
        # Attributes
        registrar.add_attribute_model("writeAllNdAttributes",
                                      self.write_all_nd_attributes,
                                      self.write_all_nd_attributes.set_value)
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
                  fileDir,  # type: scanning.hooks.AFileDir
                  formatName="det",  # type: scanning.hooks.AFormatName
                  fileTemplate="%s.h5",  # type: scanning.hooks.AFileTemplate
                  ):
        # type: (...) -> scanning.hooks.UInfos
        # On initial configure, expect to get the demanded number of frames
        self.done_when_reaches = completed_steps + steps_to_do
        self.uniqueid_offset = 0
        # Calculate how long to wait before marking this scan as stalled
        assert generator.duration > 0, \
            "Can only do constant exposure for now"
        self.frame_timeout = FRAME_TIMEOUT + generator.duration
        child = context.block_view(self.mri)
        # For first run then open the file
        # Enable position mode before setting any position related things
        child.positionMode.put_value(True)
        # Setup our required settings
        file_dir = fileDir.rstrip(os.sep)
        filename = fileTemplate % formatName
        assert "." in filename, \
            "File extension for %r should be supplied" % filename
        futures = child.put_attribute_values_async(dict(
            enableCallbacks=True,
            fileWriteMode="Stream",
            swmrMode=True,
            storeAttr=True,
            dimAttDatasets=True,
            lazyOpen=True,
            arrayCounter=0,
            filePath=file_dir + os.sep,
            fileName=formatName,
            fileTemplate="%s" + fileTemplate))
        futures += set_dimensions(child, generator)
        xml = make_layout_xml(generator, part_info,
                              self.write_all_nd_attributes.value)
        self.layout_filename = os.path.join(
            file_dir, "%s-layout.xml" % self.mri)
        with open(self.layout_filename, "w") as f:
            f.write(xml)
        layout_filename = self.layout_filename
        if self.runs_on_windows:
            layout_filename = FilePathTranslatorInfo.translate_filepath(
                part_info, self.layout_filename)
        futures += child.put_attribute_values_async(dict(
            xmlLayout=layout_filename,
            flushDataPerNFrames=steps_to_do,
            flushAttrPerNFrames=0))
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
        self.last_id_update = None
        child = context.block_view(self.mri)
        child.uniqueId.subscribe_value(self.update_completed_steps)
        f_done = child.when_value_matches_async(
            "uniqueId", self.done_when_reaches)
        while True:
            try:
                context.wait_all_futures(f_done, timeout=1)
            except TimeoutError:
                # This is ok, means we aren't done yet, so flush
                self._flush_if_still_writing(child)
                # Check it hasn't been too long
                if self.last_id_update:
                    if time.time() > self.last_id_update + self.frame_timeout:
                        raise TimeoutError(
                            "HDF writer stalled, last updated at %s" % (
                                self.last_id_update))
                # TODO: what happens if we miss the last frame?
            else:
                return

    def _flush_if_still_writing(self, child):
        # Check that the start_future hasn't errored
        if self.start_future.done():
            # This will raise if it errored
            self.start_future.result()
        else:
            # Flush the hdf frames to disk
            child.flushNow()

    @add_call_types
    def post_run_ready(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Do one last flush and then we're done
        child = context.block_view(self.mri)
        self._flush_if_still_writing(child)

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
        child.stop()

    def update_completed_steps(self, value):
        # type: (int) -> None
        completed_steps = value + self.uniqueid_offset
        self.last_id_update = time.time()
        self.registrar.report(scanning.infos.RunProgressInfo(completed_steps))
