import os

from malcolm.core import method_takes, REQUIRED, Part
from malcolm.core.vmetas import PointGeneratorMeta, StringMeta
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.infos.ADCore.datasetproducedinfo import DatasetProducedInfo


class VdsWrapperPart(Part):
    @RunnableController.Abort
    @RunnableController.Reset
    def abort(self, task):
        # Close the VDS file if it is open
        pass

    def _create_dataset_infos(self, generator, filename):
        uniqueid_path = "/entry/NDAttributes/NDArrayUniqueId"
        data_path = "/entry/detector/detector"
        sum_path = "/entry/sum/sum"
        generator_rank = len(generator.index_dims)

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
        for dim in generator.axes:
            yield DatasetProducedInfo(
                name="%s.value_set" % dim, filename=filename,
                type="position_set", rank=1,
                path="/entry/detector/%s_set" % dim, uniqueid="")

    @RunnableController.Configure
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
        "fileDir", StringMeta("File dir to write HDF files into"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        self.done_when_reaches = completed_steps + steps_to_do
        filename = os.path.join(params.fileDir, "EXCALIBUR.h5")
        # Open output HDF file
        # Write "/entry/NDAttributes/NDArrayUniqueId" blank INT32 dataset node
        # Write "/entry/detector" node with with hardlinks to everything except stripe_hdf:"/entry/detector/detector"
        # Write "/entry/sum" node with with hardlinks to everything except stripe_hdf:"/entry/sum/sum"
        # Write "/entry/sum/sum" blank FLOAT64 dataset node
        # Use subprocess call with anaconda python on vds_gen to make "/entry/detector/detector"
        # Return the dataset information
        dataset_infos = list(self._create_dataset_infos(
            params.generator, filename))

        return dataset_infos

    @RunnableController.PostRunReady
    @RunnableController.Seek
    def seek(self, task, completed_steps, steps_to_do, part_info):
        self.done_when_reaches = completed_steps + steps_to_do

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, task, update_completed_steps):
        # Monitor 6 stripe inputs and generate NDArrayUniqueId as minimum of 6 stripe NDArrayUniqueId, and sum as sum of 6 stripe sums.
        # Return when we have processed unique id self.done_when_reaches
        pass
