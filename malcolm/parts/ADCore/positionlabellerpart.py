from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import PointGeneratorMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 1000

# How far to load ahead
N_LOAD_AHEAD = 4


class PositionLabellerPart(ChildPart):
    # Stored generator for positions
    generator = None
    # The last index we have loaded
    end_index = 0
    # Where we should stop loading points
    steps_up_to = 0
    # Future for plugin run
    start_future = None
    # If we are currently loading then block loading more points
    loading = False

    def _make_xml(self, start_index):

        # Make xml root
        root_el = ET.Element("pos_layout")
        dimensions_el = ET.SubElement(root_el, "dimensions")

        # Make an index for every hdf index
        for i in range(len(self.generator.dimensions)):
            ET.SubElement(dimensions_el, "dimension", name="d%d" % i)

        # Add the a file close command for the HDF writer
        ET.SubElement(dimensions_el, "dimension", name="FilePluginClose")

        # Add the actual positions
        positions_el = ET.SubElement(root_el, "positions")

        end_index = start_index + POSITIONS_PER_XML
        if end_index > self.steps_up_to:
            end_index = self.steps_up_to

        for i in range(start_index, end_index):
            point = self.generator.get_point(i)
            if i == self.generator.size - 1:
                do_close = True
            else:
                do_close = False
            positions = dict(FilePluginClose="%d" % do_close)
            for j, value in enumerate(point.indexes):
                positions["d%d" % j] = str(value)
            position_el = ET.Element("position", **positions)
            positions_el.append(position_el)

        xml = et_to_string(root_el)
        xml_length = len(xml)
        assert xml_length < XML_MAX_SIZE, "XML size %d too big" % xml_length
        return xml, end_index

    @RunnableController.Reset
    def reset(self, task):
        super(PositionLabellerPart, self).reset(task)
        self.abort(task)

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        # clear out old subscriptions
        task.unsubscribe_all()
        self.generator = params.generator
        # Delete any remaining old positions
        futures = task.post_async(self.child["delete"])
        futures += task.put_many_async(self.child, dict(
            enableCallbacks=True,
            idStart=completed_steps + 1))
        self.steps_up_to = completed_steps + steps_to_do
        xml, self.end_index = self._make_xml(completed_steps)
        # Wait for the previous puts to finish
        task.wait_all(futures)
        # Put the xml
        task.put(self.child["xml"], xml)
        # Start the plugin
        self.start_future = task.post_async(self.child["start"])

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, task, update_completed_steps):
        self.loading = False
        task.subscribe(self.child["qty"], self.load_more_positions, task)
        task.wait_all(self.start_future)

    def load_more_positions(self, number_left, task):
        if not self.loading and self.end_index < self.steps_up_to and \
                        number_left < POSITIONS_PER_XML * N_LOAD_AHEAD:
            self.loading = True
            xml, self.end_index = self._make_xml(self.end_index)
            task.put(self.child["xml"], xml)
            self.loading = False

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, task):
        task.post(self.child["stop"])
