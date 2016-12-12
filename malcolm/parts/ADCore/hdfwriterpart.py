import os
from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED, Info
from malcolm.core.vmetas import StringMeta, PointGeneratorMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo, \
    dataset_types


SUFFIXES = "NXY3456789"


# Produced by plugins in part_info
class DatasetSourceInfo(Info):
    def __init__(self, name, type, rank, attr=None):
        self.name = name
        assert type in dataset_types, \
            "Dataset type %s not in %s" % (type, dataset_types)
        self.type = type
        self.rank = rank
        self.attr = attr


class HDFWriterPart(ChildPart):
    # Attributes
    datasets = None

    # Future for the start action
    start_future = None
    array_future = None
    done_when_reaches = 0

    def _get_dataset_infos(self, part_info, primary=True):
        filtered_datasets = []
        for dataset_info in DatasetSourceInfo.filter_values(part_info):
            if primary == (dataset_info.type == "primary"):
                filtered_datasets.append(dataset_info)
        if primary:
            assert len(filtered_datasets) in (0, 1), \
                "More than one primary datasets defined %s" % filtered_datasets
        return filtered_datasets

    def _create_dataset_infos(self, part_info, generator, filename):
        # Update the dataset table
        uniqueid = "/entry/NDAttributes/NDArrayUniqueId"
        ret = []

        # Get the detector name from the primary source
        primary_infos = self._get_dataset_infos(part_info, primary=True)

        # Add the primary datasource
        generator_rank = len(generator.index_dims)
        if primary_infos:
            dataset_info = primary_infos[0]
            ret.append(DatasetProducedInfo(
                name="%s.data" % dataset_info.name, filename=filename,
                type=dataset_info.type, rank=dataset_info.rank + generator_rank,
                path="/entry/detector/detector",
                uniqueid=uniqueid))

        # Add all the other datasources
        for dataset_info in self._get_dataset_infos(part_info, primary=False):
            path = "/entry/%s/%s" % (dataset_info.name, dataset_info.name)
            if dataset_info.type == "secondary":
                # something like xspress3.sum
                assert primary_infos, \
                    "Needed a primary dataset for secondary"
                name = "%s.%s" % (primary_infos[0].name, dataset_info.name)
                rank = primary_infos[0].rank + generator_rank
            elif dataset_info.type == "monitor":
                name = "%s.data" % dataset_info.name
                rank = dataset_info.rank + generator_rank
            else:
                # something like x.value or izero.value
                name = "%s.value" % dataset_info.name
                rank = dataset_info.rank + generator_rank
            ret.append(DatasetProducedInfo(
                name=name, filename=filename, type=dataset_info.type,
                rank=rank, path=path, uniqueid=uniqueid))

        # Add any setpoint dimensions
        for dim in generator.axes:
            ret.append(DatasetProducedInfo(
                name="%s.value_set" % dim, filename=filename,
                type="position_set", rank=1,
                path="/entry/detector/%s_set" % dim, uniqueid=""))
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
        # TODO: this should be different for windows detectors
        file_path = params.filePath.rstrip(os.sep)
        file_dir, filename = file_path.rsplit(os.sep, 1)
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
            fileName=filename,
            fileTemplate="%s%s"))
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
        dataset_infos = self._create_dataset_infos(
            part_info, params.generator, filename)
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

    @RunnableController.Abort
    def abort(self, task):
        task.post(self.child["stop"])

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

    def _make_nxdata(self, dataset_info, entry_el, generator, link=False):
        # Make a dataset for the data
        data_el = ET.SubElement(entry_el, "group", name=dataset_info.name)
        ET.SubElement(data_el, "attribute", name="signal", source="constant",
                      value=dataset_info.name, type="string")
        pad_dims = []
        for n in generator.index_names:
            if n in generator.position_units:
                pad_dims.append("%s_set" % n)
            else:
                pad_dims.append(".")
        pad_dims += ["."] * dataset_info.rank
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
        primary_infos = self._get_dataset_infos(part_info, primary=True)
        if not primary_infos:
            # Still need to put the data in the file, so manufacture something
            primary_rank = 1
        else:
            primary_rank = primary_infos[0].rank
        # Always put it in /entry/detector/detector
        primary_info = DatasetSourceInfo(
            name="detector", type="primary", rank=primary_rank)
        root_el = ET.Element("hdf5_layout")
        entry_el = ET.SubElement(root_el, "group", name="entry")
        ET.SubElement(entry_el, "attribute", name="NX_class",
                      source="constant", value="NXentry", type="string")
        # Make an nxdata element with the detector data in it
        data_el = self._make_nxdata(primary_info, entry_el, generator)
        det_el = ET.SubElement(data_el, "dataset", name=primary_info.name,
                               source="detector", det_default="true")
        ET.SubElement(det_el, "attribute", name="NX_class",
                      source="constant", value="SDS", type="string")
        # Now add some additional sources of data
        for dataset_info in self._get_dataset_infos(part_info, primary=False):
            # if we are a secondary source, use the same rank as the det
            if dataset_info.type == "secondary":
                dataset_info.rank = primary_rank
            attr_el = self._make_nxdata(
                dataset_info, entry_el, generator, link=True)
            ET.SubElement(attr_el, "dataset", name=dataset_info.name,
                          source="ndattribute", ndattribute=dataset_info.attr)
        # Add a group for attributes
        NDAttributes_el = ET.SubElement(entry_el, "group", name="NDAttributes",
                                        ndattr_default="true")
        ET.SubElement(NDAttributes_el, "attribute", name="NX_class",
                      source="constant", value="NXcollection", type="string")
        xml = et_to_string(root_el)
        return xml
