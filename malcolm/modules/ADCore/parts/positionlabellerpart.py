from typing import Tuple

from annotypes import Any, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning
from malcolm.modules.scanning.hooks import AGenerator

from ..util import FRAME_TIMEOUT

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 5000

# How far to load ahead
N_LOAD_AHEAD = 4


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("xml", "enableCallbacks", "idStart", "arrayCounter")
class PositionLabellerPart(builtin.parts.ChildPart):
    """Part for controlling a `position_labeller_block` in a scan"""

    # Stored generator for positions
    generator: AGenerator = None
    # The last index we have loaded
    end_index = None
    # Future for plugin run
    start_future = None
    # If we are currently loading then block loading more points
    loading = None
    # The uniqueID of the first point in the next run
    id_start = 0
    # When arrayCounter gets to here we are done
    done_when_reaches = 0
    # Timeout before saying we have stalled
    frame_timeout = 0.0

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)
        registrar.hook(scanning.hooks.SeekHook, self.on_seek)
        registrar.hook(scanning.hooks.PostRunArmedHook, self.on_post_run_armed)
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(
            (scanning.hooks.AbortHook, scanning.hooks.PauseHook), self.on_abort
        )

    @add_call_types
    def on_reset(self, context: scanning.hooks.AContext) -> None:
        super().on_reset(context)
        self.on_abort(context)

    def setup_plugin(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        initial_configure=True,
    ) -> None:
        # Work out the last expected ID
        if initial_configure:
            # This is an initial configure, so reset start ID to 1
            id_start = 1
            self.done_when_reaches = steps_to_do
        else:
            # This is rewinding or setting up for another batch,
            # skip to a uniqueID that has not been produced yet
            id_start = self.done_when_reaches + 1
            self.done_when_reaches += steps_to_do

        # Delete any remaining old positions
        child = context.block_view(self.mri)
        futures = [child.delete_async()]
        futures += child.put_attribute_values_async(
            dict(enableCallbacks=True, idStart=id_start, arrayCounter=id_start - 1)
        )
        xml, self.end_index = self._make_xml(completed_steps)
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Put the xml
        child.xml.put_value(xml)
        # Start the plugin
        self.start_future = child.start_async()

    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        generator: scanning.hooks.AGenerator,
    ) -> None:
        # clear out old subscriptions
        context.unsubscribe_all()
        self.generator = generator
        # Calculate how long to wait before marking this scan as stalled
        self.frame_timeout = FRAME_TIMEOUT
        if generator.duration > 0:
            self.frame_timeout += generator.duration
        else:
            # Double it to be safe
            self.frame_timeout += FRAME_TIMEOUT

        # Set up the plugin
        self.setup_plugin(context, completed_steps, steps_to_do)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        self.loading = False
        child = context.block_view(self.mri)
        child.qty.subscribe_value(self.load_more_positions, child)
        child.when_value_matches(
            "arrayCounterReadback",
            self.done_when_reaches,
            event_timeout=self.frame_timeout,
        )

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext) -> None:
        child = context.block_view(self.mri)
        child.stop()

    @add_call_types
    def on_post_run_armed(
        self, context: scanning.hooks.AContext, steps_to_do: scanning.hooks.AStepsToDo
    ) -> None:
        # clear out old subscriptions
        context.unsubscribe_all()
        self.done_when_reaches += steps_to_do

    @add_call_types
    def on_seek(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
    ) -> None:
        # clear out old subscriptions
        context.unsubscribe_all()
        # We need to set up the plugin again when pausing
        self.setup_plugin(
            context, completed_steps, steps_to_do, initial_configure=False
        )

    def load_more_positions(self, number_left: int, child: Any) -> None:
        if self.end_index and self.generator.size:
            if (
                not self.loading
                and self.end_index < self.generator.size
                and number_left < POSITIONS_PER_XML * N_LOAD_AHEAD
            ):
                self.loading = True
                xml, self.end_index = self._make_xml(self.end_index)
                child.xml.put_value(xml)
                self.loading = False

    def _make_xml(self, start_index: int) -> Tuple[str, int]:

        # Make xml root
        xml = '<?xml version="1.0" ?><pos_layout><dimensions>'

        # Make an index for every hdf index
        assert self.generator, "No generator"
        for i in range(len(self.generator.dimensions)):
            xml += '<dimension name="d%d" />' % i

        # Add the actual positions
        xml += "</dimensions><positions>"

        end_index = start_index + POSITIONS_PER_XML
        assert self.generator.size, "Generator is empty"
        if end_index > self.generator.size:
            end_index = self.generator.size

        for i in range(start_index, end_index):
            point = self.generator.get_point(i)
            xml += "<position"
            for j, value in enumerate(point.indexes):
                xml += ' d%d="%s"' % (j, value)
            xml += " />"

        xml += "</positions></pos_layout>"
        xml_length = len(xml)
        assert xml_length < XML_MAX_SIZE, "XML size %d too big" % xml_length
        return xml, end_index
