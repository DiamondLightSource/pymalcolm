from xml.etree import cElementTree as ET

from annotypes import TYPE_CHECKING, add_call_types, Any

from malcolm.compat import et_to_string
from malcolm.core import APartName, PartRegistrar
from malcolm.modules import builtin, scanning

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 1000

# How far to load ahead
N_LOAD_AHEAD = 4

if TYPE_CHECKING:
    from typing import Tuple


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save(
    "xml", "enableCallbacks", "idStart", "qty", "arrayCounter")
class PositionLabellerPart(builtin.parts.ChildPart):
    """Part for controlling a `position_labeller_block` in a scan"""

    # Stored generator for positions
    generator = None
    # The last index we have loaded
    end_index = None
    # Where we should stop loading points
    steps_up_to = None
    # Future for plugin run
    start_future = None
    # If we are currently loading then block loading more points
    loading = None
    # When arrayCounter gets to here we are done
    done_when_reaches = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PositionLabellerPart, self).setup(registrar)
        # Hooks
        registrar.hook((scanning.hooks.ConfigureHook,
                        scanning.hooks.PostRunArmedHook,
                        scanning.hooks.SeekHook), self.configure)
        registrar.hook((scanning.hooks.RunHook,
                        scanning.hooks.ResumeHook), self.run)
        registrar.hook((scanning.hooks.AbortHook,
                        scanning.hooks.PauseHook), self.abort)

    @add_call_types
    def reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(PositionLabellerPart, self).reset(context)
        self.abort(context)

    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  generator,  # type: scanning.hooks.AGenerator
                  ):
        # type: (...) -> None
        # clear out old subscriptions
        context.unsubscribe_all()
        self.generator = generator
        # Work out the offset between the generator index and uniqueID
        if completed_steps == 0:
            # The detector will reset, so the first uniqueId (for index 0)
            # will be 1
            id_start = 1
            self.done_when_reaches = steps_to_do
        else:
            # This is rewinding or setting up for another batch, so the detector
            # will skip to a uniqueID that has not been produced yet
            id_start = self.done_when_reaches + 1
            self.done_when_reaches += steps_to_do
        # Delete any remaining old positions
        child = context.block_view(self.mri)
        futures = [child.delete_async()]
        futures += child.put_attribute_values_async(dict(
            enableCallbacks=True,
            idStart=id_start))
        self.steps_up_to = completed_steps + steps_to_do
        xml, self.end_index = self._make_xml(completed_steps)
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Put the xml
        child.xml.put_value(xml)
        # Start the plugin
        self.start_future = child.start_async()

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        self.loading = False
        child = context.block_view(self.mri)
        child.qty.subscribe_value(self.load_more_positions, child)
        context.wait_all_futures(self.start_future)

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
        child.stop()

    def load_more_positions(self, number_left, child):
        # type: (int, Any) -> None
        if not self.loading and self.end_index < self.steps_up_to and \
                number_left < POSITIONS_PER_XML * N_LOAD_AHEAD:
            self.loading = True
            xml, self.end_index = self._make_xml(self.end_index)
            child.xml.put_value(xml)
            self.loading = False

    def _make_xml(self, start_index):
        # type: (int) -> Tuple[str, int]

        # Make xml root
        root_el = ET.Element("pos_layout")
        dimensions_el = ET.SubElement(root_el, "dimensions")

        # Make an index for every hdf index
        for i in range(len(self.generator.dimensions)):
            ET.SubElement(dimensions_el, "dimension", name="d%d" % i)

        # Add the actual positions
        positions_el = ET.SubElement(root_el, "positions")

        end_index = start_index + POSITIONS_PER_XML
        if end_index > self.steps_up_to:
            end_index = self.steps_up_to

        for i in range(start_index, end_index):
            point = self.generator.get_point(i)
            positions = {}
            for j, value in enumerate(point.indexes):
                positions["d%d" % j] = str(value)
            position_el = ET.Element("position", **positions)
            positions_el.append(position_el)

        xml = et_to_string(root_el)
        xml_length = len(xml)
        assert xml_length < XML_MAX_SIZE, "XML size %d too big" % xml_length
        return xml, end_index
