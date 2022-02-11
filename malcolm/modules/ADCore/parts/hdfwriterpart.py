import os
import time
from typing import Dict, Iterator, List, Optional
from xml.etree import cElementTree as ET

from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator, Dimension

from malcolm.compat import et_to_string
from malcolm.core import (
    APartName,
    Block,
    BooleanMeta,
    Future,
    Info,
    PartRegistrar,
    TimeoutError,
    Widget,
    config_tag,
)
from malcolm.modules import builtin, scanning

from ..infos import (
    CalculatedNDAttributeDatasetInfo,
    FilePathTranslatorInfo,
    NDArrayDatasetInfo,
    NDAttributeDatasetInfo,
)
from ..util import FRAME_TIMEOUT, APartRunsOnWindows, make_xml_filename

PartInfo = Dict[str, List[Info]]

SUFFIXES = "NXY3456789"

with Anno("Toggle writing of all ND attributes to HDF file"):
    AWriteAllNDAttributes = bool

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
APartRunsOnWindows = APartRunsOnWindows


def greater_than_zero(v: int) -> bool:
    return v > 0


def create_dataset_infos(
    name: str,
    part_info: scanning.hooks.APartInfo,
    generator: CompoundGenerator,
    filename: str,
) -> Iterator[Info]:
    # Update the dataset table
    uniqueid = "/entry/NDAttributes/NDArrayUniqueId"
    generator_rank = len(generator.dimensions)

    # Get the detector name from the primary source
    ndarray_infos: List[NDArrayDatasetInfo] = NDArrayDatasetInfo.filter_values(
        part_info
    )
    assert len(ndarray_infos) in (0, 1), (
        "More than one NDArrayDatasetInfo defined %s" % ndarray_infos
    )

    # Default detector rank is 2d
    detector_rank = 2

    # Add the primary datasource
    if ndarray_infos:
        ndarray_info = ndarray_infos[0]
        detector_rank = ndarray_info.rank
        yield scanning.infos.DatasetProducedInfo(
            name="%s.data" % name,
            filename=filename,
            type=scanning.util.DatasetType.PRIMARY,
            rank=detector_rank + generator_rank,
            path="/entry/detector/detector",
            uniqueid=uniqueid,
        )

        # Add any secondary datasources
        calculated_infos: List[
            CalculatedNDAttributeDatasetInfo
        ] = CalculatedNDAttributeDatasetInfo.filter_values(part_info)
        for calculated_info in calculated_infos:
            yield scanning.infos.DatasetProducedInfo(
                name="%s.%s" % (name, calculated_info.name),
                filename=filename,
                type=scanning.util.DatasetType.SECONDARY,
                rank=detector_rank + generator_rank,
                path="/entry/%s/%s" % (calculated_info.name, calculated_info.name),
                uniqueid=uniqueid,
            )

    # Add all the other datasources
    dataset_infos: List[NDAttributeDatasetInfo] = NDAttributeDatasetInfo.filter_values(
        part_info
    )
    for dataset_info in dataset_infos:
        yield scanning.infos.DatasetProducedInfo(
            name=dataset_info.name,
            filename=filename,
            type=dataset_info.type,
            # All attributes share the same rank as the detector image
            rank=detector_rank + generator_rank,
            path=f"/entry/{dataset_info.name}/{dataset_info.name}",
            uniqueid=uniqueid,
        )

    # Add any setpoint dimensions
    for dim in generator.axes:
        yield scanning.infos.DatasetProducedInfo(
            name="%s.value_set" % dim,
            filename=filename,
            type=scanning.util.DatasetType.POSITION_SET,
            rank=1,
            path="/entry/detector/%s_set" % dim,
            uniqueid="",
        )


def set_dimensions(child: Block, generator: CompoundGenerator) -> List[Future]:
    num_dims = len(generator.dimensions)
    assert num_dims <= 10, "Can only do 10 dims, you gave me %s" % num_dims
    attr_dict: Dict = dict(numExtraDims=num_dims - 1)
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


def make_set_points(
    dimension: Dimension, axis: str, data_el: ET.Element, units: str
) -> None:
    axis_vals = ["%.12g" % p for p in dimension.get_positions(axis)]
    axis_el = ET.SubElement(
        data_el,
        "dataset",
        name="%s_set" % axis,
        source="constant",
        type="float",
        value=",".join(axis_vals),
    )
    if units:
        ET.SubElement(
            axis_el,
            "attribute",
            name="units",
            source="constant",
            value=units,
            type="string",
        )


def make_nxdata(
    name: str,
    rank: int,
    entry_el: ET.Element,
    generator: CompoundGenerator,
    link: bool = False,
) -> ET.Element:
    # Make a dataset for the data
    data_el = ET.SubElement(entry_el, "group", name=name)
    ET.SubElement(
        data_el,
        "attribute",
        name="signal",
        source="constant",
        value=name,
        type="string",
    )
    pad_dims = []
    for d in generator.dimensions:
        if len(d.axes) == 1:
            pad_dims.append("%s_set" % d.axes[0])
        else:
            pad_dims.append(".")

    pad_dims += ["."] * rank
    ET.SubElement(
        data_el,
        "attribute",
        name="axes",
        source="constant",
        value=",".join(pad_dims),
        type="string",
    )
    ET.SubElement(
        data_el,
        "attribute",
        name="NX_class",
        source="constant",
        value="NXdata",
        type="string",
    )
    # Add in the indices into the dimensions array that our axes refer to
    for i, d in enumerate(generator.dimensions):
        for axis in d.axes:
            ET.SubElement(
                data_el,
                "attribute",
                name="%s_set_indices" % axis,
                source="constant",
                value=str(i),
                type="string",
            )
            if link:
                ET.SubElement(
                    data_el,
                    "hardlink",
                    name="%s_set" % axis,
                    target="/entry/detector/%s_set" % axis,
                )
            else:
                make_set_points(d, axis, data_el, generator.units[axis])
    return data_el


def make_layout_xml(
    generator: CompoundGenerator,
    part_info: scanning.hooks.APartInfo,
    write_all_nd_attributes: bool = False,
) -> str:
    # Make a root element with an NXEntry
    root_el = ET.Element("hdf5_layout", auto_ndattr_default="false")
    entry_el = ET.SubElement(root_el, "group", name="entry")
    ET.SubElement(
        entry_el,
        "attribute",
        name="NX_class",
        source="constant",
        value="NXentry",
        type="string",
    )

    # Check that there is only one primary source of detector data
    ndarray_infos: List[NDArrayDatasetInfo] = NDArrayDatasetInfo.filter_values(
        part_info
    )
    if not ndarray_infos:
        # Still need to put the data in the file, so manufacture something
        primary_rank = 2
    else:
        primary_rank = ndarray_infos[0].rank

    # Make an NXData element with the detector data in it in
    # /entry/detector/detector
    data_el = make_nxdata("detector", primary_rank, entry_el, generator)
    det_el = ET.SubElement(
        data_el, "dataset", name="detector", source="detector", det_default="true"
    )
    ET.SubElement(
        det_el,
        "attribute",
        name="NX_class",
        source="constant",
        value="SDS",
        type="string",
    )

    # Now add any calculated sources of data
    calc_dataset_infos: List[
        CalculatedNDAttributeDatasetInfo
    ] = CalculatedNDAttributeDatasetInfo.filter_values(part_info)
    for calc_dataset_info in calc_dataset_infos:
        # if we are a secondary source, use the same rank as the det
        attr_el = make_nxdata(
            calc_dataset_info.name, primary_rank, entry_el, generator, link=True
        )
        ET.SubElement(
            attr_el,
            "dataset",
            name=calc_dataset_info.name,
            source="ndattribute",
            ndattribute=calc_dataset_info.attr,
        )

    # And then any other attribute sources of data
    dataset_infos: List[NDAttributeDatasetInfo] = NDAttributeDatasetInfo.filter_values(
        part_info
    )
    for dataset_info in dataset_infos:
        # if we are a secondary source, use the same rank as the det
        attr_el = make_nxdata(
            dataset_info.name, primary_rank, entry_el, generator, link=True
        )
        ET.SubElement(
            attr_el,
            "dataset",
            name=dataset_info.name,
            source="ndattribute",
            ndattribute=dataset_info.attr,
        )

    # Add a group for attributes
    ndattr_default = "true" if write_all_nd_attributes else "false"
    nd_attributes_el = ET.SubElement(
        entry_el, "group", name="NDAttributes", ndattr_default=ndattr_default
    )
    ET.SubElement(
        nd_attributes_el,
        "attribute",
        name="NX_class",
        source="constant",
        value="NXcollection",
        type="string",
    )
    ET.SubElement(
        nd_attributes_el,
        "dataset",
        name="NDArrayUniqueId",
        source="ndattribute",
        ndattribute="NDArrayUniqueId",
    )
    ET.SubElement(
        nd_attributes_el,
        "dataset",
        name="NDArrayTimeStamp",
        source="ndattribute",
        ndattribute="NDArrayTimeStamp",
    )

    xml = et_to_string(root_el)
    return xml


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save(
    "positionMode",
    "enableCallbacks",
    "fileWriteMode",
    "swmrMode",
    "storeAttr",
    "dimAttDatasets",
    "lazyOpen",
    "arrayCounter",
    "filePath",
    "fileName",
    "fileTemplate",
    "numExtraDims",
    "flushAttrPerNFrames",
    "xmlLayout",
    "flushDataPerNFrames",
    "numCapture",
)
@builtin.util.no_save("posNameDim%s" % SUFFIXES[i] for i in range(10))
@builtin.util.no_save("extraDimSize%s" % SUFFIXES[i] for i in range(10))
class HDFWriterPart(builtin.parts.ChildPart):
    """Part for controlling an `hdf_writer_block` in a Device"""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        runs_on_windows: APartRunsOnWindows = False,
        write_all_nd_attributes: AWriteAllNDAttributes = True,
    ) -> None:
        super().__init__(name, mri)
        # Future for the start action
        self.start_future: Optional[Future] = None
        self.first_array_future: Optional[Future] = None
        self.done_when_captured = 0
        # This is when the readback for number of frames captured last updated
        self.last_capture_update: Optional[float] = None
        # Store number of frames captured for progress reporting
        self.num_captured_offset = 0
        # The HDF5 layout file we write to say where the datasets go
        self.layout_filename: Optional[str] = None
        self.runs_on_windows = runs_on_windows
        # How long to wait between frame updates before error
        self.frame_timeout = 0.0
        self.write_all_nd_attributes = BooleanMeta(
            "Toggles whether all NDAttributes are written to "
            "file, or only those specified in the dataset",
            writeable=True,
            tags=[Widget.CHECKBOX.tag(), config_tag()],
        ).create_attribute_model(write_all_nd_attributes)

    @add_call_types
    def on_reset(self, context: scanning.hooks.AContext) -> None:
        super().on_reset(context)
        self.on_abort(context)
        # HDFWriter might have still be writing so stop doesn't guarantee
        # flushed all frames start_future is in a different context so
        # can't wait for it, so just wait for the running attribute to be false
        child = context.block_view(self.mri)
        child.when_value_matches("running", False)
        # Delete the layout XML file
        if self.layout_filename and os.path.isfile(self.layout_filename):
            os.remove(self.layout_filename)
            child.xmlLayout.put_value("")

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)
        registrar.hook(
            (scanning.hooks.PostRunArmedHook, scanning.hooks.SeekHook), self.on_seek
        )
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(scanning.hooks.PostRunReadyHook, self.on_post_run_ready)
        registrar.hook(scanning.hooks.AbortHook, self.on_abort)
        # Attributes
        registrar.add_attribute_model(
            "writeAllNdAttributes",
            self.write_all_nd_attributes,
            self.write_all_nd_attributes.set_value,
        )
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(self.on_configure))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        fileDir: scanning.hooks.AFileDir,
        formatName: scanning.hooks.AFormatName = "det",
        fileTemplate: scanning.hooks.AFileTemplate = "%s.h5",
    ) -> scanning.hooks.UInfos:
        # What the capture readback value should say at the end of the run
        self.done_when_captured = completed_steps + steps_to_do
        self.num_captured_offset = 0
        # Calculate how long to wait before marking this scan as stalled
        self.frame_timeout = FRAME_TIMEOUT
        if generator.duration > 0:
            self.frame_timeout += generator.duration
        else:
            # Double it to be safe
            self.frame_timeout += FRAME_TIMEOUT
        child = context.block_view(self.mri)
        # For first run then open the file
        # Enable position mode before setting any position related things
        child.positionMode.put_value(True)
        # Setup our required settings
        file_dir = fileDir.rstrip(os.sep)
        if self.runs_on_windows:
            h5_file_dir = FilePathTranslatorInfo.translate_filepath(part_info, file_dir)
        else:
            h5_file_dir = file_dir
        filename = fileTemplate % formatName
        assert "." in filename, "File extension for %r should be supplied" % filename
        futures = child.put_attribute_values_async(
            dict(
                enableCallbacks=True,
                fileWriteMode="Stream",
                swmrMode=True,
                storeAttr=True,
                dimAttDatasets=True,
                lazyOpen=True,
                arrayCounter=0,
                filePath=h5_file_dir + os.sep,
                fileName=formatName,
                fileTemplate="%s" + fileTemplate,
            )
        )
        futures += set_dimensions(child, generator)
        xml = make_layout_xml(generator, part_info, self.write_all_nd_attributes.value)
        self.layout_filename = make_xml_filename(file_dir, self.mri, suffix="layout")
        assert self.layout_filename, "No layout filename"
        with open(self.layout_filename, "w") as f:
            f.write(xml)
        layout_filename_pv_value = self.layout_filename
        if self.runs_on_windows:
            layout_filename_pv_value = FilePathTranslatorInfo.translate_filepath(
                part_info, self.layout_filename
            )
        futures += child.put_attribute_values_async(
            dict(
                xmlLayout=layout_filename_pv_value,
                flushDataPerNFrames=steps_to_do,
                flushAttrPerNFrames=0,
            )
        )
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Reset numCapture back to 0
        child.numCapture.put_value(0)
        # Create a future for the file capture
        self.start_future = child.start_async()
        # Create a future waiting for the first array
        self.first_array_future = child.when_value_matches_async(
            "arrayCounterReadback", greater_than_zero
        )
        # Check XML
        self._check_xml_is_valid(child)
        # Return the dataset information
        dataset_infos = list(
            create_dataset_infos(formatName, part_info, generator, filename)
        )
        return dataset_infos

    def _check_xml_is_valid(self, child):
        assert child.xmlLayoutValid.value, "%s: invalid XML layout file (%s)" % (
            self.mri,
            child.xmlErrorMsg.value,
        )

    @add_call_types
    def on_seek(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
    ) -> None:
        # Reset array counter to zero so we can check for the first frame
        # to arrive in the plugin
        child = context.block_view(self.mri)
        child.arrayCounter.put_value(0)
        # Calculate the expected number of captured frames. This is in case
        # pausing has resulted in extra frames that will be overwritten
        # using the position plugin when resuming.
        num_captured = child.numCapturedReadback.value
        # Offset for progress updates
        self.num_captured_offset = num_captured - completed_steps
        # Expected captured readback after this batch
        self.done_when_captured = num_captured + steps_to_do

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # Wait for the first array to arrive in the plugin without a timeout
        context.wait_all_futures(self.first_array_future)

        # Get the child block
        child = context.block_view(self.mri)

        # Update progress based on number of frames written
        child.numCapturedReadback.subscribe_value(self.update_completed_steps)

        # Wait for the number of captured frames to reach the target
        f_done = child.when_value_matches_async(
            "numCapturedReadback", self.done_when_captured
        )
        self.last_capture_update = None
        while True:
            try:
                # Use a regular timeout so we can request a manual flush every second
                context.wait_all_futures(f_done, timeout=1)
            except TimeoutError:
                # This is ok, means we aren't done yet, so flush
                self._flush_if_still_writing(child)
                # Check it hasn't been too long since the last frame was written
                if self._has_file_writing_stalled():
                    timeout_message = self._get_file_writing_stalled_error_message(
                        child
                    )
                    raise TimeoutError(timeout_message)
            else:
                break

    def _flush_if_still_writing(self, child):
        # Check that the start_future hasn't errored
        if self.start_future.done():
            # This will raise if it errored
            self.start_future.result()
        else:
            # Flush the hdf frames to disk
            child.flushNow()

    def _has_file_writing_stalled(self) -> bool:
        if self.last_capture_update:
            return time.time() > self.last_capture_update + self.frame_timeout
        return False

    def _get_file_writing_stalled_error_message(self, child) -> str:
        unique_id = child.uniqueId.value
        num_captured = child.numCapturedReadback.value - self.num_captured_offset
        frames_expected = self.done_when_captured - self.num_captured_offset
        return (
            f"{self.name}: writing stalled at {num_captured}/{frames_expected} "
            f"captured (readback offset is {self.num_captured_offset}). "
            f"Last update was {self.last_capture_update}, "
            f"last uniqueId received in plugin was {unique_id}"
        )

    @add_call_types
    def on_post_run_ready(self, context: scanning.hooks.AContext) -> None:
        # Do one last flush and then we're done
        child = context.block_view(self.mri)
        self._flush_if_still_writing(child)

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext) -> None:
        child = context.block_view(self.mri)
        child.stop()

    def update_completed_steps(self, value: int) -> None:
        completed_steps = value - self.num_captured_offset
        self.last_capture_update = time.time()
        # Stop negative values being reported for first call when subscribing
        # when we have a non-zero offset.
        if completed_steps >= 0:
            assert self.registrar, "No registrar assigned"
            self.registrar.report(scanning.infos.RunProgressInfo(completed_steps))
