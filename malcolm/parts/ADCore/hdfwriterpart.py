import os
from xml.etree import cElementTree as ET
from collections import namedtuple

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, PointGeneratorMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo


SUFFIXES = "NXY3456789"

# Produced by plugins in part_info
# TODO: use Info subclass
DatasetSourceInfo = namedtuple("DatasetSourceInfo", "name,type")


class HDFWriterPart(ChildPart):
    # Attributes
    datasets = None

    # Future for the start action
    start_future = None
    array_future = None
    done_when_reaches = 0

    def _create_dataset_infos(self, part_info, file_path):
        # Update the dataset table
        ret = []
        for dataset_infos in part_info.values():
            for dataset_info in dataset_infos:
                path = "/entry/%s/%s" % (dataset_info.name, dataset_info.name),
                ret.append(DatasetProducedInfo(
                    name=dataset_info.name,
                    filename=file_path,
                    type=dataset_info.type,
                    path=path,
                    uniqueid="/entry/NDAttributes/NDArrayUniqueId"))
        return ret

    @RunnableController.Reset
    def reset(self, task):
        super(HDFWriterPart, self).reset(task)
        self.abort(task)

    @RunnableController.Configure
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
        "filePath", StringMeta("File path to write data to"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        self.done_when_reaches = completed_steps + steps_to_do
        # For first run then open the file
        # Enable position mode before setting any position related things
        task.put(self.child["positionMode"], True)
        # Setup our required settings
        futures = task.put_many_async(self.child, dict(
            enableCallbacks=True,
            fileWriteMode="Stream",
            swmrMode=True,
            positionMode=True,
            dimAttDatasets=True,
            lazyOpen=True,
            arrayCounter=0))
        futures += self._set_file_path(task, params.filePath)
        futures += self._set_dimensions(task, params.generator)
        xml = self._make_layout_xml(params.generator, part_info)
        futures += task.put_async(self.child["xml"], xml)
        # Wait for the previous puts to finish
        task.wait_all(futures)
        # Reset numCapture back to 0
        task.put(self.child["numCapture"], 0)
        # Start the plugin
        self.start_future = task.post_async(self.child["start"])
        # Start a future waiting for the first array
        self.array_future = task.when_matches_async(
            self.child["arrayCounter"], 1)
        # Return the dataset information
        dataset_infos = self._create_dataset_infos(part_info, params.filePath)
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
    def run(self, task, update_completed_steps):
        task.wait_all(self.array_future)
        id_ = task.subscribe(
            self.child["uniqueId"], update_completed_steps, self)
        # TODO: what happens if we miss the last frame?
        task.when_matches(self.child["uniqueId"], self.done_when_reaches)
        # TODO: why do we need this? Tasks should have been recreated...
        task.unsubscribe(id_)

    @RunnableController.PostRunIdle
    def post_run_idle(self, task):
        # If this is the last one, wait until the file is closed
        task.wait_all(self.start_future)

    @RunnableController.Abort
    def abort(self, task):
        task.post(self.child["stop"])

    def _set_file_path(self, task, file_path):
        # TODO: this should be different for windows detectors
        file_path = file_path.rstrip(os.sep)
        file_dir, file_name = file_path.rsplit(os.sep, 1)
        assert "." in file_name, \
            "File extension for %r should be supplied" % file_name
        futures = task.put_many_async(self.child, dict(
            filePath=file_dir + os.sep,
            fileName=file_name,
            fileTemplate="%s%s"))
        return futures

    def _set_dimensions(self, task, generator):
        num_dims = len(generator.index_dims)
        assert num_dims <= 10, \
            "Can only do 10 dims, you gave me %s" % num_dims
        attr_dict = dict(numExtraDims=num_dims-1)
        # Fill in dim name and size
        for i in range(10):
            suffix = SUFFIXES[i]
            if i < len(generator.index_names):
                index_name = generator.index_names[-i - 1]
                index_size = generator.index_dims[-i - 1]
            else:
                index_name = ""
                index_size = 1
            attr_dict["posNameDim%s" % suffix] = index_name
            attr_dict["extraDimSize%s" % suffix] = index_size
        futures = task.put_many_async(self.child, attr_dict)
        return futures

    def _find_generator_index(self, generator, dim):
        ndims = 0
        for g in generator.generators:
            if dim in g.position_units:
                return ndims, g
            else:
                ndims += len(g.index_dims)
        raise ValueError("Can't find generator for %s" % dim)

    def _make_nxdata(self, name, entry_el, generator, link=False):
        # Make a dataset for the data
        data_el = ET.SubElement(entry_el, "group", name=name)
        ET.SubElement(data_el, "attribute", name="signal", source="constant",
                      value=name, type="string")
        pad_dims = []
        for n in generator.index_names:
            if n in generator.position_units:
                pad_dims.append("%s_set" % n)
            else:
                pad_dims.append(".")
        # TODO: assume a 2D detector here
        pad_dims += [".", "."]
        ET.SubElement(data_el, "attribute", name="axes", source="constant",
                      value=",".join(pad_dims), type="string")
        ET.SubElement(data_el, "attribute", name="NX_class", source="constant",
                      value="NXdata", type="string")
        # Add in the indices into the dimensions array that our axes refer to
        for dim, units in sorted(generator.position_units.items()):
            # Find the generator for this dimension
            ndims, g = self._find_generator_index(generator, dim)
            ET.SubElement(data_el, "attribute",
                          name="%s_set_indices" % dim,
                          source="constant", value=str(ndims), type="string")
            if link:
                ET.SubElement(data_el, "hardlink",
                              name="%s_set" % dim,
                              target="/entry/detector/%s_set" % dim)
            else:
                axes_vals = []
                for point in g.iterator():
                    axes_vals.append("%.12g" % point.positions[dim])
                axis_el = ET.SubElement(
                    data_el, "dataset", name="%s_set" % dim,
                    source="constant", type="float", value=",".join(axes_vals))
                ET.SubElement(axis_el, "attribute", name="units",
                              source="constant", value=units, type="string")
        return data_el

    def _make_layout_xml(self, generator, part_info):
        # Check that there is only one primary source of detector data
        primary_name = ""
        additional_names = []
        for dataset_infos in part_info.values():
            for dataset_info in dataset_infos:
                if dataset_info.type == "primary":
                    assert not primary_name, "Already defined a primary dataset"
                    primary_name = dataset_info.name
                else:
                    additional_names.append(dataset_info.name)
        if not primary_name:
            primary_name = "detector"
        root_el = ET.Element("hdf5_layout")
        entry_el = ET.SubElement(root_el, "group", name="entry")
        ET.SubElement(entry_el, "attribute", name="NX_class",
                      source="constant", value="NXentry", type="string")
        # Make an nxdata element with the detector data in it
        data_el = self._make_nxdata(primary_name, entry_el, generator)
        det_el = ET.SubElement(data_el, "dataset", name=primary_name,
                               source="detector", det_default="true")
        ET.SubElement(det_el, "attribute", name="NX_class",
                      source="constant", value="SDS", type="string")
        # Now add some additional sources of data
        for attr_name in additional_names:
            attr_el = self._make_nxdata(
                attr_name, entry_el, generator, link=True)
            ET.SubElement(attr_el, "dataset", name=attr_name,
                          source="ndattribute", ndattribute=attr_name)
        # Add a group for attributes
        NDAttributes_el = ET.SubElement(entry_el, "group", name="NDAttributes",
                                        ndattr_default="true")
        ET.SubElement(NDAttributes_el, "attribute", name="NX_class",
                      source="constant", value="NXcollection", type="string")
        xml = et_to_string(root_el)
        return xml