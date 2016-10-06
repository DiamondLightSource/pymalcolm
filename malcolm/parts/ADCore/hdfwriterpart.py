import os
from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED, Task
from malcolm.core.vmetas import BooleanMeta, StringMeta, PointGeneratorMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController

SUFFIXES = "NXY3456789"

@method_takes(
    "name", StringMeta("Name of the part"), REQUIRED,
    "child", StringMeta("Name of child object"), REQUIRED,
    "merit_attr", StringMeta("Name of NDAttribute for our figure of merit"),
        "StatsMean"
)
class HDFWriterPart(LayoutPart):
    # Future for the start action
    start_future = None

    def _set_file_path(self, task, file_path):
        # TODO: this should be different for windows detectors
        file_path = file_path.rstrip(os.sep)
        file_dir, file_name = file_path.rsplit(os.sep, 1)
        assert "." in file_name, \
            "File extension for %r should be supplied" % file_name
        futures = task.put_async({
            self.child["filePath"]: file_dir + os.sep,
            self.child["fileName"]: file_name,
            self.child["fileTemplate"]: "%s%s"})
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
                index_name = generator.index_names[-i - 1] + "_index"
                index_size = generator.index_dims[-i - 1]
            else:
                index_name = ""
                index_size = 1
            attr_dict["posNameDim%s" % suffix] = index_name
            attr_dict["extraDimSize%s" % suffix] = index_size
        # Convert strings to child attributes
        attr_dict = {self.child[k]: v for k, v in attr_dict.items()}
        futures = task.put_async(attr_dict)
        return futures

    def _make_nxdata(self, name, entry_el, generator, signal_name, link=False):
        # Make a dataset for the data
        data_el = ET.SubElement(entry_el, "group", name=name)
        ET.SubElement(data_el, "attribute", name="signal", source="constant",
                      value=signal_name, type="string")
        pad_dims = ["%s_demand" % n for n in generator.index_names]
        # TODO: assume a 2D detector here
        pad_dims += [".", "."]
        ET.SubElement(data_el, "attribute", name="axes", source="constant",
                      value=",".join(pad_dims), type="string")
        ET.SubElement(data_el, "attribute", name="NX_class", source="constant",
                      value="NXdata", type="string")
        # Add in the indices into the dimensions array that our axes refer to
        for i, dim in enumerate(generator.index_names):
            ET.SubElement(data_el, "attribute",
                          name="{}_demand_indices".format(dim),
                          source="constant", value=str(i), type="string")
        for dim, units in sorted(generator.position_units.items()):
            if link:
                ET.SubElement(data_el, "hardlink",
                              name="{}_demand".format(dim),
                              target="/entry/data/{}_demand".format(dim))
            else:
                axis_el = ET.SubElement(
                    data_el, "dataset", name="{}_demand".format(dim),
                    source="ndattribute", ndattribute=dim)
                ET.SubElement(axis_el, "attribute", name="units",
                              source="constant", value=units, type="string")
        return data_el

    def _make_layout_xml(self, generator):
        root_el = ET.Element("hdf5_layout")
        entry_el = ET.SubElement(root_el, "group", name="entry")
        ET.SubElement(entry_el, "attribute", name="NX_class",
                      source="constant", value="NXentry", type="string")
        # Make an nxdata element with the detector data in it
        data_el = self._make_nxdata(
            "data", entry_el, generator, "det1")
        det1_el = ET.SubElement(data_el, "dataset", name="det1",
                                source="detector", det_default="true")
        ET.SubElement(det1_el, "attribute", name="NX_class",
                      source="constant", value="SDS", type="string")
        # Now add some figure of merit
        merit = self.params.merit_attr
        merit_el = self._make_nxdata(
            merit, entry_el, generator, merit, link=True)
        ET.SubElement(merit_el, "dataset", name=merit,
                      source="ndattribute", ndattribute=merit)
        # Add a group for attributes
        NDAttributes_el = ET.SubElement(entry_el, "group", name="NDAttributes",
                                        ndattr_default="true")
        ET.SubElement(NDAttributes_el, "attribute", name="NX_class",
                      source="constant", value="NXcollection", type="string")
        xml = et_to_string(root_el)
        return xml

    @RunnableController.Configuring
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
        "filePath", StringMeta("File path to write data to"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        if completed_steps != 0:
            # Can't reopen HDF file, so configure() after pause() does nothing
            return
        # Enable position mode before setting any position related things
        task.put(self.child["positionMode"], True)
        # Setup our required settings
        futures = task.put_async({
            self.child["enableCallbacks"]: True,
            self.child["fileWriteMode"]: "Stream",
            self.child["swmrMode"]: True,
            self.child["positionMode"]: True,
            self.child["dimAttDatasets"]: True,
            self.child["lazyOpen"]: True,
        })
        futures += self._set_file_path(task, params.filePath)
        futures += self._set_dimensions(task, params.generator)
        xml = self._make_layout_xml(params.generator)
        futures += task.put_async(self.child["xml"], xml)
        # Wait for the previous puts to finish
        task.wait_all(futures)
        # Reset numCapture back to 0
        task.put(self.child["numCapture"], 0)
        # Start the plugin
        self.start_future = task.post_async(self.child["start"])

    @RunnableController.Running
    def run(self, task, update_completed_steps):
        """Wait for run to finish
        Args:
            task (Task): The task helper
        """
        task.subscribe(self.child["uniqueId"], update_completed_steps)
        task.wait_all(self.start_future)

    @RunnableController.Aborting
    @method_takes(
        "pause", BooleanMeta("Is this an abort for a pause?"), REQUIRED)
    def abort(self, task, params):
        if not params.pause:
            task.post(self.child["stop"])
