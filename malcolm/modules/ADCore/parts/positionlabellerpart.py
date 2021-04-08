from typing import Tuple

from annotypes import Any, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning
from malcolm.modules.scanning.hooks import AGenerator

# How big an XML file can the EPICS waveform receive?
XML_MAX_SIZE = 1000000 - 2

# How many to load each time
POSITIONS_PER_XML = 5000

# How far to load ahead
N_LOAD_AHEAD = 4


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("xml", "enableCallbacks", "idStart", "qty", "arrayCounter")
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
    # The uniqueID of the last point in the scan
    id_end = 0

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(
            (scanning.hooks.ConfigureHook, scanning.hooks.SeekHook,), self.on_configure,
        )
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(
            (scanning.hooks.AbortHook, scanning.hooks.PauseHook), self.on_abort
        )

    @add_call_types
    def on_reset(self, context: scanning.hooks.AContext) -> None:
        super().on_reset(context)
        self.on_abort(context)

    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        generator: scanning.hooks.AGenerator,
    ) -> None:
        # clear out old subscriptions
        context.unsubscribe_all()
        self.generator = generator
        # Work out the offset between the generator index and uniqueID
        if completed_steps == 0:
            # The detector will reset, so the first uniqueID (for index 0) will be 1
            id_start = 1
            # The last uniqueID will be the last point in the generator
            self.id_end = generator.size
        else:
            # This is rewinding, so the detector will skip to a uniqueID that could not
            # have been produced in the original range, i.e. one more than the end
            id_start = self.id_end + 1
            # The new end will be the new start plus the remaining points
            self.id_end += generator.size - completed_steps

        # Delete any remaining old positions
        child = context.block_view(self.mri)
        futures = [child.delete_async()]
        futures += child.put_attribute_values_async(
            dict(enableCallbacks=True, idStart=id_start)
        )
        xml, self.end_index = self._make_xml(completed_steps)
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Put the xml
        child.xml.put_value(xml)
        # Start the plugin
        self.start_future = child.start_async()

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        self.loading = False
        child = context.block_view(self.mri)
        child.qty.subscribe_value(self.load_more_positions, child)

    @add_call_types
    def on_abort(self, context: scanning.hooks.AContext) -> None:
        child = context.block_view(self.mri)
        child.stop()

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
