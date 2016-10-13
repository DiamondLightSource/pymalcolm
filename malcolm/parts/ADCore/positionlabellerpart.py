from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED, Task
from malcolm.core.vmetas import PointGeneratorMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 500


class PositionLabellerPart(LayoutPart):
    # Stored generator for positions
    generator = None
    # Next position we need to generate
    end_index = 0
    # Where we should stop loading points
    steps_up_to = 0
    # Future for plugin run
    start_future = None
    # If we are currently loading
    loading = False

    def _make_xml(self, start_index):

        # Make xml root
        root_el = ET.Element("pos_layout")
        dimensions_el = ET.SubElement(root_el, "dimensions")

        # Make an index for every hdf index
        for index_name in sorted(self.generator.index_names):
            ET.SubElement(dimensions_el, "dimension", name=index_name)

        # Add the a file close command for the HDF writer
        ET.SubElement(dimensions_el, "dimension", name="FilePluginClose")

        # Add the actual positions
        positions_el = ET.SubElement(root_el, "positions")

        end_index = start_index + POSITIONS_PER_XML
        if end_index > self.steps_up_to:
            end_index = self.steps_up_to

        for i in range(start_index, end_index):
            point = self.generator.get_point(i)
            if i == self.generator.num - 1:
                do_close = True
            else:
                do_close = False
            positions = dict(FilePluginClose="%d" % do_close)
            for name, value in zip(self.generator.index_names, point.indexes):
                positions[name] = str(value)
            position_el = ET.Element("position", **positions)
            positions_el.append(position_el)

        xml = et_to_string(root_el)
        xml_length = len(xml)
        assert xml_length < XML_MAX_SIZE, "XML size %d too big" % xml_length
        return xml, end_index

    @RunnableController.Configuring
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        self.generator = params.generator
        # Delete any remaining old positions
        futures = task.post_async(self.child["delete"])
        futures += task.put_async({
            self.child["enableCallbacks"]: True,
            self.child["idStart"]: completed_steps + 1
        })
        self.steps_up_to = completed_steps + steps_to_do
        xml, self.end_index = self._make_xml(completed_steps)
        # Wait for the previous puts to finish
        task.wait_all(futures)
        # Put the xml
        task.put(self.child["xml"], xml)
        # Start the plugin
        self.start_future = task.post_async(self.child["start"])

    @RunnableController.Running
    def run(self, task, _):
        """Wait for run to finish
        Args:
            task (Task): The task helper
        """
        self.loading = False
        id_ = task.subscribe(self.child["qty"], self.load_more_positions, task)
        task.wait_all(self.start_future)
        task.unsubscribe(id_)

    def load_more_positions(self, number_left, task):
        if not self.loading and number_left < POSITIONS_PER_XML and \
                        self.end_index < self.steps_up_to:
            self.loading = True
            xml, self.end_index = self._make_xml(self.end_index)
            task.put(self.child["xml"], xml)
            self.loading = False

    @RunnableController.Aborting
    def abort(self, task):
        task.post(self.child["stop"])
