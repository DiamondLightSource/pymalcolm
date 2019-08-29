import collections
import os

import h5py
import numpy as np
from annotypes import add_call_types, TYPE_CHECKING

from malcolm.core import APartName, Info, PartRegistrar
from malcolm.modules import builtin, scanning, pmac

if TYPE_CHECKING:
    from typing import List, Dict

    PartInfo = Dict[str, List[Info]]

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri

PVar = collections.namedtuple('PVar', 'path file p_number')


# QUESTIONS:
# Where does code come from? Which object etc.
# Where should files be created? links etc?
# Savu folder?
# When create files. post configure ok? or post run?
# Where get shape from?
# Output Q names?


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("fileName", "filePath")
class KinematicsSavuPart(builtin.parts.ChildPart):
    """Part for controlling an `hdf_writer_block` in a Device"""

    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(KinematicsSavuPart, self).__init__(name, mri, stateful=False)
        self.nxs_full_filename = ""
        self.vds_full_filename = ""
        self.savu_full_filename = ""
        self.savu_code_lines = []
        self.savu_variables = {}
        self.p_vars = []
        self.use_min_max = True
        self.savu_file = None
        self.layout_table = None
        self.cs_port = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(KinematicsSavuPart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.configure)
        registrar.hook(scanning.hooks.PostConfigureHook, self.post_configure)
        registrar.hook(scanning.hooks.PostRunReadyHook, self.post_run_ready)

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  fileDir,  # type: scanning.hooks.AFileDir
                  axesToMove,  # type: scanning.hooks.AAxesToMove
                  formatName="savu",  # type: scanning.hooks.AFormatName
                  fileTemplate="%s.nxs",  # type: scanning.hooks.AFileTemplate
                  ):
        # type: (...) -> None

        self.p_vars = []
        self.use_min_max = True
        self.savu_variables = {}
        self.savu_code_lines = []

        # On initial configure, expect to get the demanded number of frames
        child = context.block_view(self.mri)
        pmac_mri = child.pmac.value

        # Derive file path from template as AreaDetector would normally do
        fileName = fileTemplate.replace('%s', formatName)
        vds_fileName = fileTemplate.replace('%s', formatName + "_vds")
        savu_fileName = formatName + "_processed.nxs"

        # This is path to the file to pass to Savu
        self.nxs_full_filename = os.path.join(fileDir, fileName)

        # This is the path to the VDS file which links to the processed Savu
        # file with the output datasets
        self.vds_full_filename = os.path.join(fileDir, vds_fileName)

        # This is the path the the processed file created by Savu after having
        # done the processing
        savu_path = os.path.join(fileDir, "savuproc")
        self.savu_full_filename = os.path.join(savu_path, savu_fileName)

        # Get the cs port mapping for this PMAC
        # {scannable: MotorInfo}
        self.layout_table = context.block_view(pmac_mri).layout.value
        axis_mapping = pmac.util.cs_axis_mapping(
            context, self.layout_table, axesToMove
        )

        # All axes will be in the same cs_port, so just use the first cs_port
        for mapping in axis_mapping.values():
            self.cs_port = mapping.cs_port
            break

        assert "." in self.nxs_full_filename, \
            "File extension for %r should be supplied" % self.nxs_full_filename

    @add_call_types
    def post_configure(self, context, part_info):
        # type: (scanning.hooks.AContext, scanning.hooks.APartInfo) -> None
        # Get the axis number for the inverse kinematics mapped in this cs_port
        # {scannable: axis_num}

        axis_numbers = pmac.util.cs_axis_numbers(
            context, self.layout_table, self.cs_port
        )

        # Map these in the file
        dataset_infos = scanning.infos.DatasetProducedInfo.filter_values(
            part_info
        )
        for scannable, axis_num in axis_numbers.items():
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
            self.p_vars.append(PVar(
                path=value_i.path, file=value_i.filename,
                p_number="p%dmean" % axis_num)
            )
            if min_i and max_i:
                self.p_vars.append(
                    PVar(
                        path=min_i.path, file=min_i.filename,
                        p_number="p%dmin" % axis_num
                    )
                )
                self.p_vars.append(PVar(path=max_i.path, file=max_i.filename,
                                        p_number="p%dmax" % axis_num))
            else:
                self.use_min_max = False

        # Get Forward Kinematics code lines
        # TODO : this assumes only one pmac - is that OK ?
        infos = pmac.infos.PmacVariablesInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, \
                "Expected 0 or 1 PmacVariablesInfo, got %d" % len(infos)
            raw_input_vars = infos[0].all_variables
        else:
            raw_input_vars = ''

        # get any variables required for the kinematic
        infos = pmac.infos.PmacCsKinematicsInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, \
                "Expected 0 or 1 PmacCsKinematicsInfo, got %d" % len(infos)
            raw_kinematics_program_code = infos[0].forward
            raw_input_vars += " " + infos[0].q_variables
        else:
            raw_kinematics_program_code = ''

        self.savu_code_lines = raw_kinematics_program_code.splitlines()
        self.parse_input_variables(raw_input_vars)

    def parse_input_variables(self, raw_input_vars):
        try:
            for var in raw_input_vars.split(' '):
                split_var = var.split('=')
                self.savu_variables[split_var[0]] = split_var[1]
        except IndexError:
            raise ValueError("Error getting kinematic input variables")

    @add_call_types
    def post_run_ready(self, _):
        # type: (scanning.hooks.AContext) -> None
        # If this is the last one, wait until the file is closed
        # context.wait_all_futures(self.start_future)
        self.create_files()

    def create_files(self):
        """ Add in the additional information to make this into a standard nexus
        format file:-
        (a) create the standard structure under the 'entry' group with a
        subgroup for each dataset. 'set_bases' lists the data sets we make here.
        (b) save a dataset for each axis in each of the dimensions of the scan
        representing the demand position at every point in the scan.
        """
        with h5py.File(self.nxs_full_filename, 'x',
                       libver="latest") as savu_file:
            savu_file.attrs['default'] = 'entry'
            nxentry = savu_file.create_group('entry')

            nxentry.attrs["NX_class"] = 'NXentry'
            nxentry.attrs['default'] = 'inputs'
            nxcollection = nxentry.create_group('inputs')
            nxcollection.attrs["NX_class"] = 'NXcollection'

            # Program code lines dataset
            program_dset = nxcollection.create_dataset(
                'program', (len(self.savu_code_lines),),
                h5py.special_dtype(vlen=str)
            )
            program_dset[...] = self.savu_code_lines
            program_dset.attrs['long_name'] = 'Kinematic Program lines'

            # Fixed variables dataset
            comp_type = np.dtype(
                [('Name', h5py.special_dtype(vlen=str)), ('Value', 'f')]
            )
            data = np.array(self.savu_variables.items(), dtype=comp_type)

            variables_dset = nxcollection.create_dataset("variables",
                                                         (len(data),),
                                                         comp_type)
            variables_dset.attrs['long_name'] = 'Fixed program variables'
            variables_dset[...] = data

            # Use MinMax dataset
            minmax_data = np.array([self.use_min_max])
            minmax_dset = nxcollection.create_dataset("use_minmax",
                                                      data=minmax_data)
            minmax_dset.attrs['long_name'] = 'Use min and max dataset'

            # Link to external P values
            for p_var in self.p_vars:
                savu_file[
                    u"/entry/inputs/" + p_var.p_number] = h5py.ExternalLink(
                    p_var.file, p_var.path)

        self.create_vds_file()

    def create_vds_file(self):
        # hmm

        # original_shape = (9, 5, 5)
        # shape = original_shape[-2:]
        # or
        shape = (5, 5)
        original_shape = (9,) + shape

        with h5py.File(self.vds_full_filename, 'w', libver='latest') as f:
            f.require_group('/entry/')
            for datatype in ['min', 'mean', 'max']:
                for i in range(9):
                    layout = h5py.VirtualLayout(shape=shape, dtype=np.float)
                    v_source = h5py.VirtualSource(
                        self.savu_full_filename,
                        '/entry/final_result_q%s/data' % datatype,
                        shape=original_shape
                    )
                    layout[:] = v_source[i]

                    f.create_virtual_dataset(
                        '/entry/q' + str(i + 1) + datatype,
                        layout, fillvalue=0
                    )

            # Q names?
