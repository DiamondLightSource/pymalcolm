import os

from annotypes import Anno, add_call_types
import numpy as np
import h5py as h5
from vdsgen.subframevdsgenerator import SubFrameVDSGenerator

from malcolm.core import Part, APartName, PartRegistrar
from malcolm.modules import ADCore, scanning
from ..util import AFillValue


with Anno("Data type of dataset"):
    ADataType = str
with Anno("Height of stripes"):
    AStripeHeight = int
with Anno("Width of stripes"):
    AStripeWidth = int


def _create_dataset_infos(generator, filename):
    uniqueid_path = "/entry/NDAttributes/NDArrayUniqueId"
    data_path = "/entry/detector/detector"
    generator_rank = len(generator.axes)
    # Create the main detector data
    yield ADCore.infos.DatasetProducedInfo(
        name="EXCALIBUR.data",
        filename=filename,
        type=ADCore.util.DatasetType.PRIMARY,
        rank=2 + generator_rank,
        path=data_path,
        uniqueid=uniqueid_path)

    # Add any setpoint dimensions
    for axis in generator.axes:
        yield ADCore.infos.DatasetProducedInfo(
            name="%s.value_set" % axis, filename=filename,
            type=ADCore.util.DatasetType.POSITION_SET, rank=1,
            path="/entry/detector/%s_set" % axis, uniqueid="")


class VDSWrapperPart(Part):

    # Constants for class
    RAW_FILE_TEMPLATE = "FEM{}"
    CREATE = "w"
    APPEND = "a"
    READ = "r"
    ID = "/entry/NDAttributes/NDArrayUniqueId"
    SUM = "/entry/sum/sum"

    required_nodes = ["/entry/detector", "/entry/sum", "/entry/NDAttributes"]
    set_bases = ["/entry/detector", "/entry/sum"]
    default_node_tree = ["/entry/detector/axes", "/entry/detector/signal",
                         "/entry/sum/axes", "/entry/sum/signal"]

    def __init__(self, name, data_type, stripe_height, stripe_width):
        # type: (APartName, ADataType, AStripeHeight, AStripeWidth) -> None
        super(VDSWrapperPart, self).__init__(name)
        self.current_id = None
        self.done_when_reaches = None
        self.generator = None
        self.fems = [1, 2, 3, 4, 5, 6]
        self.vds_path = ""
        self.vds = None
        self.command = []
        self.raw_paths = []
        self.raw_datasets = []
        self.data_type = data_type
        self.stripe_height = stripe_height
        self.stripe_width = stripe_width
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)
        self.register_hooked((scanning.hooks.AbortHook,
                              scanning.hooks.PostRunReadyHook),
                             self.close_files)

    @add_call_types
    def reset(self, context):
        # type: (scanning.hooks.AContext) -> None
        super(VDSWrapperPart, self).reset(context)
        self.abort(context)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(VDSWrapperPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    def close_files(self):
        for file_ in self.raw_datasets + [self.vds]:
            if file_ is not None and file_.id.valid:
                self.log.info("Closing file %s", file_)
                file_.close()
        self.raw_datasets = []
        self.vds = None

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: ADCore.parts.AFileDir
                  formatName="EXCALIBUR",  # type: ADCore.parts.AFormatName
                  fileTemplate="%s.h5",  # type: ADCore.parts.AFileTemplate
                  fillValue=0,  # type: AFillValue
                  ):
        # type: (...) -> scanning.hooks.UInfos
        self.generator = generator
        self.current_id = completed_steps
        self.done_when_reaches = completed_steps + steps_to_do
        self.vds_path = os.path.join(fileDir, fileTemplate % formatName)
        raw_file_path = fileTemplate % self.RAW_FILE_TEMPLATE.format(1)
        node_tree = list(self.default_node_tree)
        for axis in generator.axes:
            for base in self.set_bases:
                node_tree.append(base + "/{}_set".format(axis))
                node_tree.append(base + "/{}_set_indices".format(axis))

        with h5.File(self.vds_path, self.CREATE, libver="latest") as self.vds:
            for node in self.required_nodes:
                self.vds.require_group(node)
            for node in node_tree:
                self.vds[node] = h5.ExternalLink(raw_file_path, node)

            # Create placeholder id and sum datasets
            initial_dims = tuple([1 for _ in generator.shape])
            initial_shape = initial_dims + (1, 1)
            max_shape = generator.shape + (1, 1)
            self.vds.create_dataset(self.ID, initial_shape,
                                    maxshape=max_shape, dtype="int32")
            self.vds.create_dataset(self.SUM, initial_shape,
                                    maxshape=max_shape, dtype="float64",
                                    fillvalue=np.nan)
        files = [fileTemplate % self.RAW_FILE_TEMPLATE.format(fem)
                 for fem in self.fems]
        shape = generator.shape + (self.stripe_height, self.stripe_width)

        # Create the VDS using vdsgen
        fgen = SubFrameVDSGenerator(
            fileDir,
            files=files,
            output=fileTemplate % formatName,
            source=dict(shape=shape, dtype=self.data_type),
            source_node="/entry/detector/detector",
            target_node="/entry/detector/detector",
            stripe_spacing=0,
            module_spacing=121,
            fill_value=fillValue,
            log_level=1  # DEBUG
        )
        fgen.generate_vds()

        # Store required attributes
        self.raw_paths = [os.path.abspath(os.path.join(fileDir, file_))
                          for file_ in files]

        # Open the VDS
        self.vds = h5.File(
                self.vds_path, self.APPEND, libver="latest", swmr=True)
        # Return the dataset information
        dataset_infos = list(_create_dataset_infos(
            generator, fileTemplate % formatName))

        return dataset_infos
