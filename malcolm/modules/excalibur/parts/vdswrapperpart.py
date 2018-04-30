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
    NUM_VDS_AXES = 2

    required_nodes = ["/entry/detector", "/entry/sum", "/entry/NDAttributes"]
    set_bases = ["/entry/detector", "/entry/sum"]
    default_node_tree = ["/entry/sum/axes", "/entry/sum/signal"]

    def __init__(self, name, data_type, stripe_height, stripe_width):
        # type: (APartName, ADataType, AStripeHeight, AStripeWidth) -> None
        super(VDSWrapperPart, self).__init__(name)
        self.fems = [1, 2, 3, 4, 5, 6]
        self.data_type = data_type
        self.stripe_height = stripe_height
        self.stripe_width = stripe_width
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(VDSWrapperPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: ADCore.parts.AFileDir
                  formatName="EXCALIBUR",  # type: ADCore.parts.AFormatName
                  fileTemplate="%s.h5",  # type: ADCore.parts.AFileTemplate
                  fillValue=0,  # type: AFillValue
                  ):
        # type: (...) -> scanning.hooks.UInfos
        vds_path = os.path.join(fileDir, fileTemplate % formatName)
        raw_file_path = fileTemplate % self.RAW_FILE_TEMPLATE.format(1)
        node_tree = list(self.default_node_tree)
        for axis in generator.axes:
            for base in self.set_bases:
                node_tree.append(base + "/{}_set".format(axis))

        pad_dims = []
        for d in generator.dimensions:
            if len(d.axes) == 1:
                pad_dims.append("%s_set" % d.axes[0])
            else:
                pad_dims.append(".")

        pad_dims += ["."] * self.NUM_VDS_AXES

        with h5.File(vds_path, self.CREATE, libver="latest") as vds:
            for node in self.required_nodes:
                vds.require_group(node)
            for node in node_tree:
                vds[node] = h5.ExternalLink(raw_file_path, node)

            vds["/entry/detector"].attrs["axes"] = ",".join(pad_dims)
            vds["/entry/detector"].attrs["signal"] = "detector"
            for i, d in enumerate(generator.dimensions):
                for axis in d.axes:
                    name = "%s_set_indices" % axis
                    vds["/entry/detector"].attrs[name] = str(i)

        # Create the VDS using vdsgen
        files = [fileTemplate % self.RAW_FILE_TEMPLATE.format(fem)
                 for fem in self.fems]
        shape = generator.shape + (self.stripe_height, self.stripe_width)
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

        # Return the dataset information
        dataset_infos = list(
            _create_dataset_infos(generator, fileTemplate % formatName))

        return dataset_infos
