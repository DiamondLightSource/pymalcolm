import os
import sys
from subprocess import check_call

sys.path.insert(0, "/dls_sw/work/tools/RHEL6-x86_64/odin/venv/lib/python2.7/"
                   "site-packages")
import h5py as h5
import numpy as np
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.core import method_takes, REQUIRED, Part
from malcolm.modules.ADCore.infos import DatasetProducedInfo
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta
from copy import deepcopy

# Number of points too look ahead of the current id index to account for dropped frames
NUM_LOOKAHEAD = 100

@method_takes(
    "name", StringMeta("Name of part"), REQUIRED,
    "dataType", StringMeta("Data type of dataset"), REQUIRED,
    "stripeHeight", NumberMeta("int16", "Height of stripes"), REQUIRED,
    "stripeWidth", NumberMeta("int16", "Width of stripes"), REQUIRED)
class VDSWrapperPart(Part):

    # Constants for vds-gen CLI app
    VENV = "/dls_sw/work/tools/RHEL6-x86_64/odin/venv/bin/python"
    VDS_GEN = "/dls_sw/work/tools/RHEL6-x86_64/odin/vds-gen/vdsgen/app.py"
    EMPTY = "-e"
    OUTPUT = "-o"
    FILES = "-f"
    SHAPE = "--shape"
    DATA_TYPE = "--data_type"
    DATA_PATH = "-d"
    STRIPE_SPACING = "-s"
    MODULE_SPACING = "-m"
    FILL_VALUE = "-F"
    SOURCE_NODE = "--source_node"
    TARGET_NODE = "--target_node"
    LOG_LEVEL = "-l"

    # Constants for class
    RAW_FILE_TEMPLATE = "FEM{}"
    OUTPUT_FILE = "EXCALIBUR"
    CREATE = "w"
    APPEND = "a"
    READ = "r"
    ID = "/entry/NDAttributes/NDArrayUniqueId"
    SUM = "/entry/sum/sum"

    required_nodes = ["/entry/detector", "/entry/sum", "/entry/NDAttributes"]
    set_bases = ["/entry/detector", "/entry/sum"]
    default_node_tree = ["/entry/detector/axes", "/entry/detector/signal",
                         "/entry/sum/axes", "/entry/sum/signal"]

    def __init__(self, params):
        self.params = params
        super(VDSWrapperPart, self).__init__(params.name)

        self.current_idx = None
        self.done_when_reaches = None
        self.generator = None
        self.fems = [1, 2, 3, 4, 5, 6]
        self.vds_path = ""
        self.vds = None
        self.command = []
        self.raw_paths = []
        self.raw_datasets = []
        self.data_type = params.dataType
        self.stripe_height = params.stripeHeight
        self.stripe_width = params.stripeWidth
        
    @RunnableController.Abort
    @RunnableController.Reset
    @RunnableController.PostRunReady
    def abort(self, context):
        self.close_files()

    def close_files(self):
        for file_ in self.raw_datasets + [self.vds]:
            if file_ is not None and file_.id.valid:
                self.log.info("Closing file %s", file_)
                file_.close()
        self.raw_datasets = []
        self.vds = None


    def _create_dataset_infos(self, generator, filename):
        uniqueid_path = "/entry/NDAttributes/NDArrayUniqueId"
        data_path = "/entry/detector/detector"
        sum_path = "/entry/sum/sum"
        generator_rank = len(generator.axes)
        # Create the main detector data
        yield DatasetProducedInfo(
            name="EXCALIBUR.data",
            filename=filename,
            type="primary",
            rank=2 + generator_rank,
            path=data_path,
            uniqueid=uniqueid_path)

        # And the sum
        yield DatasetProducedInfo(
            name="EXCALIBUR.sum",
            filename=filename,
            type="secondary",
            rank=2 + generator_rank,
            path=sum_path,
            uniqueid=uniqueid_path)

        # Add any setpoint dimensions
        for axis in generator.axes:
            yield DatasetProducedInfo(
                name="%s.value_set" % axis, filename=filename,
                type="position_set", rank=1,
                path="/entry/detector/%s_set" % axis, uniqueid="")

    @RunnableController.Configure
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED,
        "fileTemplate", StringMeta(
            """Printf style template to generate filename relative to fileDir.
            Arguments are:
              1) %s: EXCALIBUR"""), "%s.h5",
        "fillValue", NumberMeta("int32", "Fill value for stripe spacing"), 0)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        self.generator = params.generator
        self.current_idx = completed_steps
        self.done_when_reaches = completed_steps + steps_to_do
        self.vds_path = os.path.join(params.fileDir,
                                     params.fileTemplate % self.OUTPUT_FILE)
        raw_file_path = params.fileTemplate % self.RAW_FILE_TEMPLATE.format(1)
        node_tree = list(self.default_node_tree)
        for axis in params.generator.axes:
            for base in self.set_bases:
                node_tree.append(base + "/{}_set".format(axis))
                node_tree.append(base + "/{}_set_indices".format(axis))

        with h5.File(self.vds_path, self.CREATE, libver="latest") as self.vds:
            for node in self.required_nodes:
                self.vds.require_group(node)
            for node in node_tree:
                self.vds[node] = h5.ExternalLink(raw_file_path, node)

            # Create placeholder id and sum datasets
            initial_dims = tuple([1 for _ in params.generator.shape])
            initial_shape = initial_dims + (1, 1)
            max_shape = params.generator.shape + (1, 1)
            self.vds.create_dataset(self.ID, initial_shape,
                                    maxshape=max_shape, dtype="int32")
            self.vds.create_dataset(self.SUM, initial_shape,
                                    maxshape=max_shape, dtype="float64", fillvalue=np.nan)
        files = [params.fileTemplate % self.RAW_FILE_TEMPLATE.format(fem)
                 for fem in self.fems]
        shape = [str(d) for d in params.generator.shape] + \
                [str(self.stripe_height), str(self.stripe_width)]
        # Base arguments
        command = [self.VENV, self.VDS_GEN, params.fileDir]
        # Define empty and required arguments to do so
        command += [self.EMPTY,
                    self.FILES] + files + \
                   [self.SHAPE] + shape + \
                   [self.DATA_TYPE, self.data_type]
        # Override default spacing and data path
        command += [self.STRIPE_SPACING, "0",
                    self.MODULE_SPACING, "121",
                    self.FILL_VALUE, str(params.fillValue),
                    self.SOURCE_NODE, "/entry/detector/detector",
                    self.TARGET_NODE, "/entry/detector/detector"]
        # Define output file path
        command += [self.OUTPUT, params.fileTemplate % self.OUTPUT_FILE]
        command += [self.LOG_LEVEL, "1"] # str(self.log.level / 10)]
        self.log.info("VDSGen Command: %s", command)
        check_call(command)

        # Store required attributes
        self.raw_paths = [os.path.abspath(os.path.join(params.fileDir, file_))
                          for file_ in files]

        # Open the VDS
        self.vds = h5.File(
                self.vds_path, self.APPEND, libver="latest", swmr=True)
        # Return the dataset information
        dataset_infos = list(self._create_dataset_infos(
            params.generator, params.fileTemplate % self.OUTPUT_FILE))

        return dataset_infos

    @RunnableController.PostRunArmed
    @RunnableController.Seek
    def seek(self, context, completed_steps, steps_to_do, part_info):
        self.current_idx = completed_steps
        self.done_when_reaches = completed_steps + steps_to_do

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        if not self.raw_datasets:
            for path_ in self.raw_paths:
                self.log.info("Waiting for file %s to be created", path_)
                while not os.path.exists(path_):
                    context.sleep(1)
                self.raw_datasets.append(
                    h5.File(path_, self.READ, libver="latest", swmr=True))
            for dataset in self.raw_datasets:
                self.log.info("Waiting for id in file %s", dataset)
                while self.ID not in dataset:
                    context.sleep(0.1)
            # here I should grab the handles to the vds dataset, id and all the swmr datasets and ids.
            if self.vds.id.valid and self.ID in self.vds:
                self.vds.swmr_mode = True
                self.vds_sum = self.vds[self.SUM]
                self.vds_id = self.vds[self.ID]
                self.fems_sum = [ix[self.SUM] for ix in self.raw_datasets] 
                self.fems_id = [ix[self.ID] for ix in self.raw_datasets]
            else:
                self.log.warning("File %s does not exist or does not have a "
                             "UniqueIDArray, returning 0", file_)
                return 0
            
            self.previous_idx = 0
        # does this on every run
        try:
            self.log.info("Monitoring raw files until ID reaches %s",
                          self.done_when_reaches)
            while self.current_idx < self.done_when_reaches: # monitor the output of the vds id. When it counts up then we have finished.
                context.sleep(0.1)  # Allow while loop to be aborted
                indexes = self.get_modify_slices()
                self.maybe_update_datasets(indexes)

        except Exception as error:
            self.log.exception("Error in run. Message:\n%s", error.message)
            self.close_files()
            raise
        
    def maybe_update_datasets(self, indexes):
        ids = []
        for id in self.fems_id:
            id.refresh()
            shape = id.shape
            # Only select the ones in range
            if isinstance(indexes, tuple):
                # One index, unpacked                        
                if self.index_in_range(indexes, shape):
                    valid_indexes = indexes
                else:
                    valid_indexes = None
            else:
                valid_indexes = tuple(i for i in indexes if self.index_in_range(i, shape))
            if valid_indexes:
                ids.append(max(id[valid_indexes]))
            else:
                # Not ready yet, don't process
                return
        
        if min(ids) > self.current_idx: 
            # if the the fem with the lowest id is less than the vds id
            self.update_id(indexes) # update the id index
            self.update_sum(indexes) #  update the sum index
            self.log.info("ID reached: %s", self.current_idx)        

    def index_in_range(self, index, shape):
        # check the given index is valid for the shape of the array
        in_range = index < np.array(shape)[:len(index)]
        return np.all(in_range) 

    def update_id(self, indexes):
        self.vds_id.resize(self.fems_id[0].shape) # source and target are now the same shape
        new_ids = self.fems_id[0][indexes]
        for id in self.fems_id[1:]:
            new_ids = np.minimum(new_ids, id[indexes])
        self.vds_id[indexes] = new_ids # set the updated values
        self.current_idx = max(new_ids)
        self.vds_id.flush() # flush to disc

    def update_sum(self, indexes):
        self.fems_sum[0].refresh()
        new_shape = self.fems_sum[0].shape #  get the shape that we have gotten to.
        self.vds_sum.refresh()
        self.vds_sum.resize(new_shape) # source and target are now the same size
        fems_sum = self.fems_sum[0][indexes]
        for fem in self.fems_sum[1:]:
            fem.refresh()
            fems_sum += fem[indexes]
        self.vds_sum[indexes] = fems_sum
        self.vds_sum.flush()

    def get_modify_slices(self):
        # returns the slices we want to modify
        indexes = []        
        end_idx = min(self.current_idx + NUM_LOOKAHEAD, self.done_when_reaches)
        for idx in range(self.current_idx, end_idx):
            indexes.append(self.generator.get_point(idx).indexes)
        if len(indexes) == 1:
            # if indexes = [[0, 4]], return something like (0, 4)
            return tuple(indexes[0])
        else:
            # if indexes = [[0, 4], [0, 5]], return something like [(0, 0), (4, 5)]
            return zip(*indexes)
