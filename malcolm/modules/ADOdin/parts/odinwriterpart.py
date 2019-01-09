import os
import math
from xml.etree import cElementTree as ET

from annotypes import add_call_types, Anno, TYPE_CHECKING
from scanpointgenerator import CompoundGenerator, Dimension

from malcolm.compat import et_to_string
from malcolm.core import APartName, Future, Info, Block, PartRegistrar
from malcolm.modules import builtin, scanning
from malcolm.core.errors import MalcolmException

if TYPE_CHECKING:
    from typing import Iterator, List, Dict

    PartInfo = Dict[str, List[Info]]


# If the HDF writer doesn't get new frames in this time (seconds), consider it
# stalled and raise
FRAME_TIMEOUT = 60

with Anno("Directory to write data to"):
    AFileDir = str
with Anno("Argument for fileTemplate, normally filename without extension"):
    AFileName = str
with Anno("File Name"):
    AFileTemplate = str


def greater_than_zero(v):
    # type: (int) -> bool
    return v > 0


class OdinWriterPart(builtin.parts.ChildPart):
    """Part for controlling an `hdf_writer_block` in a Device"""

    def __init__(self, name, mri):
        # type: (APartName, scanning.parts.AMri) -> None
        super(OdinWriterPart, self).__init__(name, mri)
        # Future for the start action
        self.start_future = None  # type: Future
        self.array_future = None  # type: Future
        self.done_when_reaches = 0
        # CompletedSteps = arrayCounter + self.uniqueid_offset
        self.unique_id_offset = 0
        # The HDF5 layout file we write to say where the datasets go
        self.layout_filename = None  # type: str
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)
        self.register_hooked((scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.seek)
        self.register_hooked((scanning.hooks.RunHook,
                              scanning.hooks.ResumeHook), self.run)
        self.register_hooked(scanning.hooks.PostRunReadyHook,
                             self.post_run_ready)
        self.register_hooked(scanning.hooks.AbortHook, self.abort)
        self.register_hooked(scanning.hooks.PauseHook, self.pause)

    @add_call_types
    def reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(OdinWriterPart, self).reset(context)
        self.abort(context)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(OdinWriterPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    @add_call_types
    def pause(self, context):
        # type: (scanning.hooks.AContext) -> None
        raise NotImplementedError("Seek not implemented")

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir='/tmp',  # type: AFileDir
                  fileName="odin.hdf",  # type: AFileName
                  ):
        # type: (...) -> scanning.hooks.UInfos
        # On initial configure, expect to get the demanded number of frames
        self.done_when_reaches = completed_steps + steps_to_do
        self.unique_id_offset = 0
        child = context.block_view(self.mri)
        file_dir = fileDir.rstrip(os.sep)
        full_filename = os.path.join(fileDir, fileName)
        assert "." in full_filename, \
            "File extension for %r should be supplied" % full_filename
        futures = child.put_attribute_values_async(dict(
            numCapture=steps_to_do,
            filePath=file_dir + os.sep,
            fileName=fileName))
        # todo restore similar to this when Flush period control is avail
        # # We want the HDF writer to flush this often:
        # flush_time = 1  # seconds
        # # (In particular this means that HDF files can be read cleanly by
        # # SciSoft at the start of a scan.)
        # assert generator.duration > 0, \
        #     "Duration %s for generator must be >0 to signify fixed exposure" \
        #     % generator.duration
        # if generator.duration > flush_time:
        #     # We are going slower than 1/flush_time Hz, so flush every frame
        #     n_frames_between_flushes = 1
        # else:
        #     # Limit update rate to be every flush_time seconds
        #     n_frames_between_flushes = int(math.ceil(
        #         flush_time / generator.duration))
        #     # But make sure we flush in this round of frames
        #     n_frames_between_flushes = min(
        #         steps_to_do, n_frames_between_flushes)
        # futures += child.put_attribute_values_async(dict(
        #     xml=self.layout_filename,
        #     flushDataPerNFrames=n_frames_between_flushes,
        #     flushAttrPerNFrames=n_frames_between_flushes))
        # # Wait for the previous puts to finish
        context.wait_all_futures(futures)

        # Start the plugin
        self.start_future = child.start_async()
        # Start a future waiting for the first array
        self.array_future = child.when_value_matches_async(
            "numCaptured", greater_than_zero)

        # todo Return the dataset information
        # dataset_infos = list(create_dataset_infos(
        #     fileName, part_info, generator, full_filename))
        # return dataset_infos
        return None

    @add_call_types
    def seek(self,
             context,  # type: scanning.hooks.AContext
             completed_steps,  # type: scanning.hooks.ACompletedSteps
             steps_to_do,  # type: scanning.hooks.AStepsToDo
             ):
        # type: (...) -> None
        # This is rewinding or setting up for another batch, so the detector
        # will skip to a uniqueID that has not been produced yet
        self.unique_id_offset = completed_steps - self.done_when_reaches
        self.done_when_reaches += steps_to_do
        child = context.block_view(self.mri)
        # Just reset the array counter_block
        child.arrayCounter.put_value(0)
        # Start a future waiting for the first array
        self.array_future = child.when_value_matches_async(
            "numCaptured", greater_than_zero)

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        context.wait_all_futures(self.array_future)
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.numCaptured.subscribe_value(self.update_completed_steps)
        # TODO: what happens if we miss the last frame?
        child.when_value_matches(
            "numCaptured", self.done_when_reaches, event_timeout=FRAME_TIMEOUT)

    @add_call_types
    def post_run_ready(self, context):
        # type: (scanning.hooks.AContext) -> None
        # If this is the last one, wait until the file is closed
        context.wait_all_futures(self.start_future)

    @add_call_types
    def abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        child = context.block_view(self.mri)
        child.stop()

    def update_completed_steps(self, value):
        # type: (int) -> None
        completed_steps = value + self.unique_id_offset
        self.registrar.report(scanning.infos.RunProgressInfo(completed_steps))
