import os

import h5py
from annotypes import add_call_types, TYPE_CHECKING
from vdsgen import InterleaveVDSGenerator, \
    ReshapeVDSGenerator

from malcolm.core import APartName, Future, Info, PartRegistrar
from malcolm.modules import builtin, scanning

if TYPE_CHECKING:
    from typing import List, Dict

    PartInfo = Dict[str, List[Info]]

# If the HDF writer doesn't get new frames in this time (seconds), consider it
# stalled and raise
FRAME_TIMEOUT = 60


def greater_than_zero(v):
    # type: (int) -> bool
    return v > 0


def files_shape(frames, block_size, file_count):
    # all files get at least per_file blocks
    per_file = int(frames) / int(file_count * block_size)
    # this is the remainder once per_file blocks have been distributed
    remainder = int(frames) % int(file_count * block_size)

    # distribute the remainder
    remainders = [block_size if remains > block_size else remains
                  for remains in range(remainder, 0, -block_size)]
    # pad the remainders list with zeros
    remainders += [0] * (file_count - len(remainders))

    shape = tuple(int(per_file * block_size + remainders[i])
                  for i in range(file_count))
    return shape


def one_vds(vds_folder, vds_name, files, width, height,
            shape, generator, alternates, block_size, source_node,
            target_node, d_type):
    # this vds reshapes from 1 file per data writer to a single 1D data set
    gen = InterleaveVDSGenerator(
        vds_folder,
        files=files,
        source={'height': width,
                'width': height,
                'dtype': d_type,
                'shape': shape
                },
        output=vds_name,
        source_node=source_node,
        target_node="process/" + target_node + "_interleave",
        block_size=block_size,
        log_level=1)
    gen.generate_vds()

    # this VDS shapes the data to match the dimensions of the scan
    gen = ReshapeVDSGenerator(path=vds_folder,
                              files=[vds_name],
                              source_node="process/" + target_node +
                                          "_interleave",
                              target_node=target_node,
                              output=vds_name,
                              shape=generator.shape,
                              alternate=alternates,
                              log_level=1)

    gen.generate_vds()


def create_vds(generator, raw_name, vds_path, child):
    vds_folder, vds_name = os.path.split(vds_path)

    image_width = int(child.imageWidth.value)
    image_height = int(child.imageHeight.value)
    block_size = int(child.blockSize.value)
    hdf_count = int(child.numProcesses.value)
    data_type = str(child.dataType.value)

    # hdf_shape tuple represents the number of images in each file
    hdf_shape = files_shape(generator.size, block_size, hdf_count)

    alternates = (gen.alternate for gen in generator.generators)
    if any(alternates):
        raise ValueError("Snake scans are not yet supported")
    else:
        alternates = None

    files = [os.path.join(
        vds_folder, '{}_{:06d}.h5'.format(raw_name, i + 1))
        for i in range(hdf_count)]
    shape = (hdf_shape, image_height, image_width)

    # prepare a vds for the image data
    one_vds(vds_folder, vds_name, files, image_width, image_height,
            shape, generator, alternates, block_size,
            'data', 'data', data_type)

    shape = (hdf_shape, 1, 1)

    # prepare a vds for the unique IDs
    one_vds(vds_folder, vds_name, files, 1, 1,
            shape, generator, alternates, block_size,
            'UID', 'uid', 'uint64')
    # prepare a vds for the sums
    one_vds(vds_folder, vds_name, files, 1, 1,
            shape, generator, alternates, block_size,
            'SUM', 'sum', 'uint64')


set_bases = ["/entry/detector/", "/entry/detector_sum/",
             "/entry/detector_uid/"]
set_data = ["/data", "/sum", "/uid"]


def add_nexus_nodes(generator, vds_file_path):
    """ Add in the additional information to make this into a standard nexus
    format file:-
    (a) create the standard structure under the 'entry' group with a
    subgroup for each dataset. 'set_bases' lists the data sets we make here.
    (b) save a dataset for each axis in each of the dimensions of the scan
    representing the demand position at every point in the scan.
    """

    # create the axes dimensions attribute, a comma separated list giving size
    # of the axis dimensions padded with . for the detector dimensions and
    # multidimensional dimensions
    pad_dims = []
    for d in generator.dimensions:
        if len(d.axes) == 1:
            pad_dims.append("%s_set" % d.axes[0])
        else:
            pad_dims.append(".")

    pad_dims += ["."] * 2  # assume a 2 dimensional detector

    with h5py.File(vds_file_path, 'r+', libver="latest") as vds:
        for data, node in zip(set_data, set_bases):
            # create a group for this entry
            vds.require_group(node)
            # points to the axis demand data sets
            vds[node].attrs["axes"] = pad_dims
            vds[node].attrs["NX_class"] = ['NXdata']

            # points to the detector dataset for this entry
            vds[node].attrs["signal"] = data.split('/')[-1]
            # a hard link from this entry 'signal' to the actual data
            vds[node + data] = vds[data]

            axis_sets = {}
            # iterate the axes in each dimension of the generator to create the
            # axis information nodes
            for i, d in enumerate(generator.dimensions):
                for axis in d.axes:
                    # add signal data dimension for axis
                    axis_indices = '{}_set_indices'.format(axis)
                    vds[node].attrs[axis_indices] = i

                    # demand positions for axis
                    axis_set = '{}_set'.format(axis)
                    if axis_sets.get(axis_set):
                        # link to the first entry's demand list
                        vds[node + axis_set] = axis_sets[axis_set]
                    else:
                        # create the demand list for the first entry only
                        axis_demands = d.get_positions(axis)
                        vds.create_dataset(
                            node + axis_set, data=axis_demands)
                        vds[node + axis_set].attrs["units"] = \
                            generator.units[axis]
                    axis_sets[axis_set] = vds[node + axis_set]

        vds['entry'].attrs["NX_class"] = ['NXentry']


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("fileName", "filePath", "numCapture")
class OdinWriterPart(builtin.parts.ChildPart):
    """Part for controlling an `hdf_writer_block` in a Device"""

    def __init__(self, name, mri):
        # type: (APartName, builtin.parts.AMri) -> None
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
        self.exposure_time = 0

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
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: scanning.util.AFileDir
                  formatName="odin",  # type: scanning.util.AFormatName
                  fileTemplate="%s.h5",  # type: scanning.util.AFileTemplate
                  ):
        # type: (...) -> scanning.hooks.UInfos

        self.exposure_time = generator.duration

        # On initial configure, expect to get the demanded number of frames
        self.done_when_reaches = completed_steps + steps_to_do
        self.unique_id_offset = 0
        child = context.block_view(self.mri)
        file_dir = fileDir.rstrip(os.sep)

        # derive file path from template as AreaDetector would normally do
        fileName = fileTemplate.replace('%s', formatName)

        # this is path to the requested file which will be a VDS
        vds_full_filename = os.path.join(fileDir, fileName)

        # this is the path to underlying file the odin writer will write to
        raw_file_name = fileTemplate.replace('%s', formatName + '_raw_data')
        raw_file_basename, _ = os.path.splitext(raw_file_name)

        assert "." in vds_full_filename, \
            "File extension for %r should be supplied" % vds_full_filename
        futures = child.put_attribute_values_async(dict(
            numCapture=steps_to_do,
            filePath=file_dir + os.sep,
            fileName=raw_file_basename))
        context.wait_all_futures(futures)

        # Start the plugin
        self.start_future = child.start_async()
        # Start a future waiting for the first array
        self.array_future = child.when_value_matches_async(
            "numCaptured", greater_than_zero)

        create_vds(generator, raw_file_basename,
                   vds_full_filename, child)
        add_nexus_nodes(generator, vds_full_filename)

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
        child.when_value_matches(
            "numCaptured", self.done_when_reaches,
            event_timeout=self.exposure_time+FRAME_TIMEOUT)

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
