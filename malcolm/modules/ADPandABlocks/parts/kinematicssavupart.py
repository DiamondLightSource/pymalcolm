import collections
import os
from shutil import copyfile
from typing import TYPE_CHECKING, Optional

import h5py
import numpy as np
from annotypes import Anno, add_call_types

from malcolm.core import APartName, Info, PartRegistrar
from malcolm.modules import builtin, pandablocks, pmac, scanning
from malcolm.modules.builtin.util import LayoutTable

if TYPE_CHECKING:
    from typing import Dict, List

    PartInfo = Dict[str, List[Info]]

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri

with Anno("name of CS port"):
    ACsPort = str

with Anno("mri suffix of malcolm CS block [$(pmac_mri):$(suffix)]"):
    ACsMriSuffix = str

with Anno("mri suffix of malcolm Status block [$(pmac_mri):$(suffix)]"):
    AStatusMriSuffix = str

PVar = collections.namedtuple("PVar", "path file p_number")


def MRES_VAR(axis):
    return "P48%02d" % axis


def OFFSET_VAR(axis):
    return "P49%02d" % axis


# We will set these attributes on the child block, so don't save them
class KinematicsSavuPart(builtin.parts.ChildPart):
    """Part for writing out files to send to Savu for post processing
    of forward kinematics. Creates the following files:

    - <ID>-savu.nxs - Input data file for Savu. Links to Panda data, and
        datasets which contain the kinematics code and variables.
    - <ID>-savu_pl.nxs - Savu process list, copied from /kinematics directory
    - <ID>-vds.nxs - VDS file linking to Savu processed data (when processed)
    """

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        cs_port: ACsPort = None,
        cs_mri_suffix: ACsMriSuffix = ":CS",
        status_mri_suffix: AStatusMriSuffix = ":STATUS",
    ) -> None:
        super(KinematicsSavuPart, self).__init__(name, mri, stateful=False)
        self.nxs_full_filename = ""
        self.vds_full_filename = ""
        self.savu_pl_filename = ""
        self.savu_full_filename = ""
        self.savu_code_lines: List[str] = []
        self.savu_variables: Dict[str, str] = {}
        self.q_value_mapping: Dict[int, str] = {}
        self.p_vars: List[PVar] = []
        self.use_min_max = True
        self.savu_file = None
        self.layout_table: Optional[LayoutTable] = None
        self.pos_table = None
        self.cs_port = cs_port
        self.cs_mri_suffix = cs_mri_suffix
        self.status_mri_suffix = status_mri_suffix
        self.shape = None
        self.pmac_mri: str = ""
        self.panda_mri: str = ""
        self.axis_numbers: Dict[str, int] = {}
        self.generator = None

    def setup(self, registrar: PartRegistrar) -> None:
        super(KinematicsSavuPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(self.on_configure))
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)
        registrar.hook(scanning.hooks.PostConfigureHook, self.on_post_configure)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        fileDir: scanning.hooks.AFileDir,
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
        part_info: scanning.hooks.APartInfo,
        fileTemplate: scanning.hooks.AFileTemplate = "%s.nxs",
    ) -> scanning.hooks.UInfos:

        self.p_vars = []
        self.use_min_max = True
        self.savu_variables = {}
        self.savu_code_lines = []
        self.shape = generator.shape
        self.q_value_mapping = {}
        self.generator = generator

        # On initial configure, expect to get the demanded number of frames
        child = context.block_view(self.mri)
        self.pmac_mri = child.pmac.value
        self.panda_mri = child.panda.value

        # Derive file path from template
        baseTemplate = os.path.splitext(fileTemplate)[0]
        # Create the various nexus files to pass to Savu and expected output
        fileName = (baseTemplate % "savu") + ".nxs"
        vds_fileName = (baseTemplate % "kinematics-vds") + ".nxs"
        savu_pl_fileName = (baseTemplate % "savu_pl") + ".nxs"
        savu_fileName = (baseTemplate % "savu_processed") + ".nxs"

        # This is path to the file to pass to Savu
        self.nxs_full_filename = os.path.join(fileDir, fileName)

        # This is path to the process list file to pass to Savu
        self.savu_pl_filename = os.path.join(fileDir, savu_pl_fileName)

        # This is the path to the VDS file which links to the processed Savu
        # file with the output datasets
        self.vds_full_filename = os.path.join(fileDir, vds_fileName)

        # This is the path the the processed file created by Savu after having
        # done the processing
        savu_rel_path = os.path.join((baseTemplate % "savuproc"), savu_fileName)
        self.savu_full_filename = os.path.join(fileDir, savu_rel_path)

        # Get the cs port mapping for this PMAC
        # {scannable: MotorInfo}
        self.layout_table = context.block_view(self.pmac_mri).layout.value
        assert self.layout_table, "No layout table"
        axis_mapping = pmac.util.cs_axis_mapping(context, self.layout_table, axesToMove)

        if self.cs_port is None:
            # All axes will be in the same cs_port so just use the first
            for mapping in axis_mapping.values():
                self.cs_port = mapping.cs_port
                break

        # Create the mapping of output q variables to axis names
        # These correspond to the compound motors
        for mapping in axis_mapping.values():
            if mapping.cs_axis in pmac.util.CS_AXIS_NAMES:
                q_value = pmac.util.CS_AXIS_NAMES.index(mapping.cs_axis) + 1
                self.q_value_mapping[q_value] = mapping.scannable

        assert "." in self.nxs_full_filename, (
            "File extension for %r should be supplied" % self.nxs_full_filename
        )

        self.pos_table = context.block_view(self.panda_mri).positions.value
        assert self.pos_table, "No pos table"

        # Get the axis number for the inverse kinematics mapped in this cs_port
        # These are raw motors
        assert self.cs_port, "No CS port"
        self.axis_numbers = pmac.util.cs_axis_numbers(
            context, self.layout_table, self.cs_port
        )

        produced_datasets = []
        dtypes = {"mean": scanning.infos.DatasetType.POSITION_VALUE}
        for scannable, axis_num in self.axis_numbers.items():
            dataset_i = None
            for ind, name in enumerate(self.pos_table.datasetName):
                if name == scannable:
                    pos_type = self.pos_table.capture[ind]
                    if pos_type == pandablocks.util.PositionCapture.MIN_MAX_MEAN:
                        dataset_i = ind
                    elif (
                        pos_type == pandablocks.util.PositionCapture.MEAN
                        or pos_type == pandablocks.util.PositionCapture.VALUE
                    ):
                        dataset_i = ind
                        self.use_min_max = False

            # Check there was a dataset for the axis
            assert dataset_i, "No value dataset for %s" % scannable

        if self.use_min_max:
            dtypes["min"] = scanning.infos.DatasetType.POSITION_MIN
            dtypes["max"] = scanning.infos.DatasetType.POSITION_MAX
        for axis in self.q_value_mapping.values():
            rank = len(generator.dimensions)
            for k, v in dtypes.items():
                PATH = "/entry/" + axis + "." + k
                produced_datasets += [
                    scanning.infos.DatasetProducedInfo(
                        axis + "." + k, vds_fileName, v, rank, PATH, ""
                    )
                ]

        return produced_datasets

    @add_call_types
    def on_post_configure(
        self, context: scanning.hooks.AContext, part_info: scanning.hooks.APartInfo
    ) -> None:

        # Map these in the file
        dataset_infos = scanning.infos.DatasetProducedInfo.filter_values(part_info)
        for scannable, axis_num in self.axis_numbers.items():
            min_i, max_i, value_i = None, None, None
            for info in dataset_infos:
                if info.name.startswith(scannable + "."):
                    if info.type == scanning.infos.DatasetType.POSITION_MIN:
                        min_i = info
                    elif info.type == scanning.infos.DatasetType.POSITION_MAX:
                        max_i = info
                    elif info.type == scanning.infos.DatasetType.POSITION_VALUE:
                        value_i = info
            # Always make sure .value is there
            assert value_i, "No value dataset for %s" % scannable
            self.p_vars.append(
                PVar(
                    path=value_i.path,
                    file=value_i.filename,
                    p_number="p%dmean" % axis_num,
                )
            )
            if min_i and max_i:
                self.p_vars.append(
                    PVar(
                        path=min_i.path,
                        file=min_i.filename,
                        p_number="p%dmin" % axis_num,
                    )
                )
                self.p_vars.append(
                    PVar(
                        path=max_i.path,
                        file=max_i.filename,
                        p_number="p%dmax" % axis_num,
                    )
                )
            else:
                self.use_min_max = False

        # Get Forward Kinematics code lines and I,P,M,Q input variables
        pmac_status_child = context.block_view(self.pmac_mri + ":STATUS")

        raw_input_vars = " ".join(
            [
                pmac_status_child.iVariables.value,
                pmac_status_child.pVariables.value,
                pmac_status_child.mVariables.value,
            ]
        )

        pmac_cs_child = context.block_view(self.pmac_mri + ":" + self.cs_mri_suffix)

        raw_kinematics_program_code = pmac_cs_child.forwardKinematic.value
        raw_input_vars += " " + pmac_cs_child.qVariables.value

        self.savu_code_lines = raw_kinematics_program_code.splitlines()
        self.parse_input_variables(raw_input_vars)

        self.create_files()

    def check_mres_and_pos(self, split_var):
        # if PandA has MRES/Offset, clear P variable so it isn't applied twice
        for scannable, axis_num in self.axis_numbers.items():
            posbus_ind = self.pos_table.datasetName.index(scannable)
            panda_mres = self.pos_table.scale[posbus_ind]
            panda_offset = self.pos_table.offset[posbus_ind]
            if split_var[0] == MRES_VAR(axis_num):
                if panda_mres != 1.0:
                    split_var[1] = "1.0"
            elif split_var[0] == OFFSET_VAR(axis_num):
                if panda_offset != 0.0:
                    split_var[1] = "0.0"
        return split_var

    def parse_input_variables(self, raw_input_vars):
        try:
            for var in raw_input_vars.split(" "):
                if var:
                    split_var = var.split("=")
                    # ignore any values in hex
                    if not split_var[1].startswith("$"):
                        split_var = self.check_mres_and_pos(split_var)
                        self.savu_variables[split_var[0]] = split_var[1]
        except IndexError:
            raise ValueError(
                "Error getting kinematic input variables from %s" % raw_input_vars
            )

    def create_files(self):
        """Create the files that will be used by Savu
        - <ID>-savu.nxs - Input data file for Savu. Links to Panda data, and
            datasets which contain the kinematics code and variables, and
            whether to use min, mean and max datasets, or just the mean.
        - <ID>-savu_pl.nxs - Savu process list
        - <ID>-kinematics-vds.nxs - VDS file linking to Savu processed data
        """

        # Create the -savu.nxs file which contains the input data for Savu
        with h5py.File(self.nxs_full_filename, "w", libver="latest") as savu_file:
            savu_file.attrs["default"] = "entry"
            nxentry = savu_file.create_group("entry")

            nxentry.attrs["NX_class"] = "NXentry"
            nxentry.attrs["default"] = "inputs"
            nxcollection = nxentry.create_group("inputs")
            nxcollection.attrs["NX_class"] = "NXcollection"

            # Program code lines dataset
            program_dset = nxcollection.create_dataset(
                "program", (len(self.savu_code_lines),), h5py.special_dtype(vlen=str)
            )
            program_dset[...] = self.savu_code_lines
            program_dset.attrs["long_name"] = "Kinematic Program lines"

            # Fixed variables dataset
            comp_type = np.dtype(
                [("Name", h5py.special_dtype(vlen=str)), ("Value", "f")]
            )

            data = np.array(list(self.savu_variables.items()), dtype=comp_type)

            variables_dset = nxcollection.create_dataset(
                "variables", (len(data),), comp_type
            )
            variables_dset.attrs["long_name"] = "Fixed program variables"
            variables_dset[...] = data

            # Use MinMax dataset
            minmax_data = np.array([self.use_min_max])
            minmax_dset = nxcollection.create_dataset("use_minmax", data=minmax_data)
            minmax_dset.attrs["long_name"] = "Use min and max dataset"

            # Link to external P values
            for p_var in self.p_vars:
                savu_file[u"/entry/inputs/" + p_var.p_number] = h5py.ExternalLink(
                    p_var.file, p_var.path
                )

        # Create Savu plugin list file
        src = os.path.realpath(__file__)
        src = os.path.dirname(src)
        if self.use_min_max:
            kinematics_file = "min_mean_max.nxs"
        else:
            kinematics_file = "only_mean.nxs"

        src = os.path.join(src, "..", "kinematics", kinematics_file)

        copyfile(src, self.savu_pl_filename)

        # Create the finished VDS file which links to the processed Savu data
        self.create_vds_file()

    def create_vds_file(self):
        """Create the VDS file that points to the processed savu files.
        Assumes that savu is called with the argument to specify the location
        of the processed data is in a data folder with the suffix '-savuproc'
        """

        virtual_shape = (9,) + self.shape

        with h5py.File(self.vds_full_filename, "w", libver="latest") as f:
            f.require_group("/entry/")

            if self.use_min_max:
                datatypes = ["min", "mean", "max"]
            else:
                datatypes = ["mean"]

            for datatype in datatypes:
                for i in range(9):
                    layout = h5py.VirtualLayout(shape=self.shape, dtype=np.float)
                    v_source = h5py.VirtualSource(
                        self.savu_full_filename,
                        "/entry/final_result_q%s/data" % datatype,
                        shape=virtual_shape,
                    )
                    layout[:] = v_source[i]

                    # Use axis name if have it, otherwise use raw Q number
                    if i + 1 in self.q_value_mapping:
                        f.create_virtual_dataset(
                            "/entry/" + self.q_value_mapping[i + 1] + "." + datatype,
                            layout,
                            fillvalue=-1,
                        )

            # Add any setpoint dimensions
            for dim in self.generator.dimensions:
                for axis in dim.axes:
                    f.create_dataset(
                        name="/entry/%s_set/%s.value_set" % (axis, axis),
                        dtype=np.float64,
                        data=[p for p in dim.get_positions(axis)],
                    )
