import os
import math as m
from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED, Info
from malcolm.core.vmetas import StringMeta, PointGeneratorMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo, \
    dataset_types


SUFFIXES = "NXY3456789"

attribute_dataset_types = ["detector", "monitor", "position"]


# Produced by plugins in part_info
class NDAttributeDatasetInfo(Info):
    def __init__(self, name, type, attr, rank):
        self.name = name
        assert type in attribute_dataset_types, \
            "Dataset type %s not in %s" % (type, dataset_types)
        self.type = type
        self.attr = attr
        self.rank = rank


class CalculatedNDAttributeDatasetInfo(Info):
    def __init__(self, name, attr):
        self.name = name
        self.attr = attr


class NDArrayDatasetInfo(Info):
    def __init__(self, name, rank):
        self.name = name
        self.rank = rank


class HDFWriterPart(ChildPart):
    # Attributes
    datasets = None

    # Future for the start action
    start_future = None
    array_future = None
    done_when_reaches = 0

    # The HDF5 layout file we write to say where the datasets go
    layout_filename = None

    def _create_dataset_infos(self, part_info, generator, filename):
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
                name="%s.data" % ndarray_info.name, filename=filename,
                type="primary", rank=ndarray_info.rank + generator_rank,
                path="/entry/detector/detector",
                uniqueid=uniqueid)

            # Add any secondary datasources
            for calculated_info in \
                    CalculatedNDAttributeDatasetInfo.filter_values(part_info):
                yield DatasetProducedInfo(
                    name="%s.%s" % (ndarray_info.name, calculated_info.name),
                    filename=filename, type="secondary",
                    rank=ndarray_info.rank + generator_rank,
                    path="/entry/%s/%s" % (
                        calculated_info.name, calculated_info.name),
                    uniqueid=uniqueid)

        # Add all the other datasources
        for dataset_info in NDAttributeDatasetInfo.filter_values(part_info):
            if dataset_info.type == "detector":
                # Something like I0
                name = "%s.data" % dataset_info.name
                type = "primary"
            elif dataset_info.type == "monitor":
                # Something like Iref
                name = "%s.data" % dataset_info.name
                type = "monitor"
            elif dataset_info.type == "position":
                # Something like x
                name = "%s.value" % dataset_info.name
                type = "position_value"
            else:
                raise AttributeError("Bad dataset type %r, should be in %s" % (
                    dataset_info.type, attribute_dataset_types))
            yield DatasetProducedInfo(
                name=name, filename=filename, type=type,
                rank=dataset_info.rank + generator_rank,
                path="/entry/%s/%s" % (dataset_info.name, dataset_info.name),
                uniqueid=uniqueid)

        # Add any setpoint dimensions
        for dim in generator.axes:
            yield DatasetProducedInfo(
                name="%s.value_set" % dim, filename=filename,
                type="position_set", rank=1,
                path="/entry/detector/%s_set" % dim, uniqueid="")

    @RunnableController.Reset
    def reset(self, task):
        super(HDFWriterPart, self).reset(task)
        self.abort(task)

    @RunnableController.Configure
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
        "fileDir", StringMeta("Directory to write hdf file to"), REQUIRED,
        "formatName", StringMeta(
            "Name argument for fileTemplate, normally filename without extension"),
        REQUIRED,
        "fileTemplate", StringMeta(
            """Printf style template to generate filename relative to fileDir.
            Arguments are:
              1) %s: the value of formatName"""), "%s.h5")
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        self.done_when_reaches = completed_steps + steps_to_do
        # For first run then open the file
        # Enable position mode before setting any position related things
        task.put(self.child["positionMode"], True)
        # Setup our required settings
        # TODO: this should be different for windows detectors
        file_dir = params.fileDir.rstrip(os.sep)
        filename = params.fileTemplate % params.formatName
        assert "." in filename, \
            "File extension for %r should be supplied" % filename
        futures = task.put_many_async(self.child, dict(
            enableCallbacks=True,
            fileWriteMode="Stream",
            swmrMode=True,
            positionMode=True,
            dimAttDatasets=True,
            lazyOpen=True,
            arrayCounter=0,
            filePath=file_dir + os.sep,
            fileName=params.formatName,
            fileTemplate="%s" + params.fileTemplate))
        futures += self._set_dimensions(task, params.generator)
        xml = self._make_layout_xml(params.generator, part_info)
        self.layout_filename = os.path.join(
            file_dir, "%s-layout.xml" % self.params.mri)
        open(self.layout_filename, "w").write(xml)
        futures += task.put_async(self.child["xml"], self.layout_filename)
        # Wait for the previous puts to finish
        task.wait_all(futures)
        # Reset numCapture back to 0
        task.put(self.child["numCapture"], 0)
        assert params.generator.duration > 0, \
            "Duration %s for generator must be >0 to signify constant " \
            "exposure" % params.generator.duration
        # We want the HDF writer to flush this often:
        flush_time = 1  # seconds
        # (In particular this means that HDF files can be read cleanly by
        # SciSoft at the start of a scan.)
        if params.generator.duration > flush_time:
            # We are going slower than 1/flush_time Hz, so flush every frame
            n_frames_between_flushes = 1
        else:
            # Limit update rate to be every flush_time seconds
            n_frames_between_flushes = int(m.ceil(
                flush_time / params.generator.duration))
            # But make sure we flush in this round of frames
            n_frames_between_flushes = min(
                steps_to_do, n_frames_between_flushes)
        task.put(self.child["flushDataPerNFrames"], n_frames_between_flushes)
        task.put(self.child["flushAttrPerNFrames"], n_frames_between_flushes)
        # Start the plugin
        self.start_future = task.post_async(self.child["start"])
        # Start a future waiting for the first array
        self.array_future = task.when_matches_async(
            self.child["arrayCounter"], 1)
        # Return the dataset information
        dataset_infos = list(self._create_dataset_infos(
            part_info, params.generator, filename))
        return dataset_infos

    @RunnableController.PostRunReady
    @RunnableController.Seek
    def seek(self, task, completed_steps, steps_to_do, part_info):
        self.done_when_reaches = completed_steps + steps_to_do
        # Just reset the array counter
        task.put(self.child["arrayCounter"], 0)
        # Start a future waiting for the first array
        self.array_future = task.when_matches_async(
            self.child["arrayCounter"], 1)

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, task, update_completed_steps):
        task.wait_all(self.array_future)
        task.unsubscribe_all()
        task.subscribe(self.child["uniqueId"], update_completed_steps, self)
        # TODO: what happens if we miss the last frame?
        task.when_matches(self.child["uniqueId"], self.done_when_reaches)

    @RunnableController.PostRunIdle
    def post_run_idle(self, task):
        # If this is the last one, wait until the file is closed
        task.wait_all(self.start_future)
        # Delete the layout XML file
        os.remove(self.layout_filename)

    @RunnableController.Abort
    def abort(self, task):
        task.post(self.child["stop"])

    def _set_dimensions(self, task, generator):
        num_dims = len(generator.dimensions)
        assert num_dims <= 10, \
            "Can only do 10 dims, you gave me %s" % num_dims
        attr_dict = dict(numExtraDims=num_dims-1)
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
        futures = task.put_many_async(self.child, attr_dict)
        return futures

    def _make_nxdata(self, name, rank, entry_el, generator, link=False):
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
                    self._make_set_points(
                        d, axis, data_el, generator.units[axis])
        return data_el

    def _make_set_points(self, dimension, axis, data_el, units):
        axis_vals = ["%.12g" % p for p in dimension.get_positions(axis)]
        axis_el = ET.SubElement(
            data_el, "dataset", name="%s_set" % axis, source="constant",
            type="float", value=",".join(axis_vals))
        ET.SubElement(axis_el, "attribute", name="units", source="constant",
                      value=units, type="string")

    def _make_layout_xml(self, generator, part_info):
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
        data_el = self._make_nxdata(
            "detector", primary_rank, entry_el, generator)
        det_el = ET.SubElement(data_el, "dataset", name="detector",
                               source="detector", det_default="true")
        ET.SubElement(det_el, "attribute", name="NX_class",
                      source="constant", value="SDS", type="string")

        # Now add any calculated sources of data
        for dataset_info in \
                CalculatedNDAttributeDatasetInfo.filter_values(part_info):
            # if we are a secondary source, use the same rank as the det
            attr_el = self._make_nxdata(
                dataset_info.name, primary_rank, entry_el, generator, link=True)
            ET.SubElement(attr_el, "dataset", name=dataset_info.name,
                          source="ndattribute", ndattribute=dataset_info.attr)

        # And then any other attribute sources of data
        for dataset_info in NDAttributeDatasetInfo.filter_values(part_info):
            # if we are a secondary source, use the same rank as the det
            attr_el = self._make_nxdata(dataset_info.name, dataset_info.rank,
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
