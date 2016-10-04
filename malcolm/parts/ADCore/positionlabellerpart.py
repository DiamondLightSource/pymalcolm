from xml.etree import cElementTree as ET

from malcolm.core import method_takes, REQUIRED, Task
from malcolm.core.vmetas import NumberMeta
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

    def _make_xml(self, start_index):

        # Make xml root
        root_el = ET.Element("pos_layout")
        dimensions_el = ET.SubElement(root_el, "dimensions")

        # Make a demand for every position, and for the close command
        for axis_name in sorted(self.generator.position_units):
            ET.SubElement(dimensions_el, "dimension", name=axis_name)
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
            position_el = ET.Element("position", **positions)
            positions_el.append(position_el)

        xml = ET.tostring(root_el)
        xml_length = len(xml)
        assert xml_length < XML_MAX_SIZE, "XML size %d too big" % xml_length
        return xml, end_index

    @ManagerController.Configuring
    @method_takes(
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
        task.subscribe(self.child["index"], self.load_more_positions, task)
        task.wait_all(self.start_future)

    def load_more_positions(self, current_index, task):
        if current_index < POSITIONS_PER_XML and \
                        self.end_index < self.generator.num:
            xml, self.end_index = self._make_xml(self.end_index)
            task.put(self.child["xml"], xml)

    @ManagerController.Aborting
    def abort(self, task):
        task.post(self.child["stop"])
