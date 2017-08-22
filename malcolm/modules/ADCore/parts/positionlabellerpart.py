from xml.etree import cElementTree as ET

from malcolm.compat import et_to_string
from malcolm.core import method_takes, REQUIRED
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta
from malcolm.modules.ADCore.infos import UniqueIdInfo

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 1000

# How far to load ahead
N_LOAD_AHEAD = 4


class PositionLabellerPart(StatefulChildPart):
    """Part for controlling a `position_labeller_block` in a Device"""
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
    def reset(self, context):
        super(PositionLabellerPart, self).reset(context)
        self.abort(context)

    @RunnableController.Configure
    @RunnableController.PostRunArmed
    @RunnableController.Seek
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        # clear out old subscriptions
        context.unsubscribe_all()
        self.generator = params.generator
        # Work out the offset between the generator index and uniqueID
        if completed_steps == 0:
            # The detector will reset, so the first uniqueId (for index 0)
            # will be 1
            idStart = 1
        else:
            # The detector will report the last frame it produced, so the
            # first ID will be that number plus 1
            infos = UniqueIdInfo.filter_values(part_info)
            assert len(infos) == 1, \
                "Expected one uniqueId reporter, got %r" % (infos,)
            idStart = infos[0].value + 1
        # Delete any remaining old positions
        child = context.block_view(self.params.mri)
        futures = [child.delete_async()]
        futures += child.put_attribute_values_async(dict(
            enableCallbacks=True,
            idStart=idStart))
        self.steps_up_to = completed_steps + steps_to_do
        xml, self.end_index = self._make_xml(completed_steps)
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Put the xml
        child.xml.put_value(xml)
        # Start the plugin
        self.start_future = child.start_async()

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        self.loading = False
        child = context.block_view(self.params.mri)
        child.qty.subscribe_value(self.load_more_positions, child)
        context.wait_all_futures(self.start_future)

    def load_more_positions(self, number_left, child):
        if not self.loading and self.end_index < self.steps_up_to and \
                        number_left < POSITIONS_PER_XML * N_LOAD_AHEAD:
            self.loading = True
            xml, self.end_index = self._make_xml(self.end_index)
            child.xml.put_value(xml)
            self.loading = False

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, context):
        child = context.block_view(self.params.mri)
        child.stop()
