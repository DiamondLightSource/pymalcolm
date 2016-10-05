from xml.etree import cElementTree as ET

from malcolm.core import method_takes, REQUIRED, Task
from malcolm.core.vmetas import NumberMeta, TableMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.managercontroller import ManagerController, \
    configure_args

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 100


class PositionLabellerPart(LayoutPart):
    # Stored generator for positions
    generator = None
    # Next position we need to generate
    end_index = 0
    # Future for plugin run
    start_future = None
    # If we are currently loading
    loading = False

    def _make_xml(self, start_index):

        # Make xml root
        root_el = ET.Element("pos_layout")
        dimensions_el = ET.SubElement(root_el, "dimensions")

        # Make a demand for every position
        for axis_name in sorted(self.generator.position_units):
            ET.SubElement(dimensions_el, "dimension", name=axis_name)

        # Make an index for every hdf index
        for index_name in self.generator.index_names:
            index_name += "_index"
            ET.SubElement(dimensions_el, "dimension", name=index_name)

        # Add the a file close command for the HDF writer
        ET.SubElement(dimensions_el, "dimension", name="FilePluginClose")

        # Add the actual positions
        positions_el = ET.SubElement(root_el, "positions")

        end_index = start_index + POSITIONS_PER_XML
        if end_index > self.generator.num:
            end_index = self.generator.num

        for i in range(start_index, end_index):
            point = self.generator.get_point(i)
            if i == self.generator.num - 1:
                do_close = True
            else:
                do_close = False
            positions = dict(FilePluginClose="%d" % do_close)
            for name, value in point.positions.items():
                positions[name] = str(value)
            for name, value in zip(self.generator.index_names, point.indexes):
                positions["%s_index" % name] = str(value)
            position_el = ET.Element("position", **positions)
            positions_el.append(position_el)

        xml = '<?xml version="1.0" ?>' + str(ET.tostring(root_el))
        xml_length = len(xml)
        assert xml_length < XML_MAX_SIZE, "XML size %d too big" % xml_length
        return xml, end_index

    @ManagerController.Configuring
    @method_takes(
        "info_table", TableMeta(), REQUIRED,
        "start_step", NumberMeta("uint32", "Step to start at"), REQUIRED,
        *configure_args)
    def configure(self, task, params):
        self.generator = params.generator
        # Delete any remaining old positions
        futures = task.post_async(self.child["delete"])
        futures += task.put_async({
            self.child["enableCallbacks"]: True,
            self.child["idStart"]: params.start_step + 1
        })
        # Calculate the first 100 frames
        xml, self.end_index = self._make_xml(params.start_step)
        # Wait for the previous puts to finish
        task.wait_all(futures)
        # Put the xml
        task.put(self.child["xml"], xml)
        # Start the plugin
        self.start_future = task.post_async(self.child["start"])

    @ManagerController.Running
    def run(self, task):
        """Wait for run to finish
        Args:
            task (Task): The task helper
        """
        self.loading = False
        task.subscribe(self.child["qty"], self.load_more_positions, task)
        task.wait_all(self.start_future)

    def load_more_positions(self, number_left, task):
        if not self.loading and number_left < POSITIONS_PER_XML and \
                        self.end_index < self.generator.num:
            self.loading = True
            xml, self.end_index = self._make_xml(self.end_index)
            task.put(self.child["xml"], xml)
            self.loading = False

    @ManagerController.Aborting
    def abort(self, task):
        task.post(self.child["stop"])
