import os
import time

import h5py
import numpy as np
from annotypes import Anno, add_call_types
from scanpointgenerator import Point

from malcolm.core import APartName, Part, PartRegistrar
from malcolm.modules import builtin, scanning

from ..util import interesting_pattern, make_gaussian_blob

with Anno("Width of detector image"):
    AWidth = int
with Anno("Height of detector image"):
    AHeight = int


# Datasets where we will write our data
DATA_PATH = "/entry/data"
SUM_PATH = "/entry/sum"
UID_PATH = "/entry/uid"
SET_PATH = "/entry/%s_set"

# How often we flush in seconds
FLUSH_PERIOD = 1


class FileWritePart(Part):
    """Minimal interface demonstrating a file writing detector part"""

    def __init__(self, name: APartName, width: AWidth, height: AHeight) -> None:
        super().__init__(name)
        # Store input arguments
        self._width = width
        self._height = height
        # The detector image we will modify for each image (0..255 range)
        self._blob = make_gaussian_blob(width, height) * 255
        # The hdf file we will write
        self._hdf: h5py.File = None
        # Configure args and progress info
        self._exposure = 0.0
        self._generator: scanning.hooks.AGenerator = None
        self._completed_steps = 0
        self._steps_to_do = 0
        # How much to offset uid value from generator point
        self._uid_offset = 0

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)
        registrar.hook(
            (scanning.hooks.PostRunArmedHook, scanning.hooks.SeekHook), self.on_seek
        )
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook(
            (scanning.hooks.AbortHook, builtin.hooks.ResetHook), self.on_reset
        )
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(self.on_configure))

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        generator: scanning.hooks.AGenerator,
        fileDir: scanning.hooks.AFileDir,
        exposure: scanning.hooks.AExposure = 0.0,
        formatName: scanning.hooks.AFormatName = "det",
        fileTemplate: scanning.hooks.AFileTemplate = "%s.h5",
    ) -> scanning.hooks.UInfos:
        """On `ConfigureHook` create HDF file with datasets"""
        # Store args
        self._completed_steps = completed_steps
        self._steps_to_do = steps_to_do
        self._generator = generator
        self._uid_offset = 0
        self._exposure = exposure
        # Work out where to write the file
        filename = fileTemplate % formatName
        filepath = os.path.join(fileDir, filename)
        # Make the HDF file
        self._hdf = self._create_hdf(filepath)
        # Tell everyone what we're going to make
        infos = list(self._create_infos(formatName, filename))
        return infos

    # For docs: Before run
    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        """On `RunHook` record where to next take data"""
        # Start time so everything is relative
        end_of_exposure = time.time() + self._exposure
        last_flush = end_of_exposure
        assert self.registrar, "Part has no registrar"
        for i in range(
            self._completed_steps, self._completed_steps + self._steps_to_do
        ):
            # Get the point we are meant to be scanning
            point = self._generator.get_point(i)
            # Simulate waiting for an exposure and writing the data
            wait_time = end_of_exposure - time.time()
            context.sleep(wait_time)
            self.log.debug(f"Writing data for point {i}")
            self._write_data(point, i)
            # Flush the datasets if it is time to
            if time.time() - last_flush > FLUSH_PERIOD:
                last_flush = time.time()
                self._flush_datasets()
            # Schedule the end of the next exposure
            end_of_exposure += point.duration
            # Update the point as being complete
            self.registrar.report(scanning.infos.RunProgressInfo(i + 1))
        # Do one last flush and then we're done
        self._flush_datasets()

    @add_call_types
    def on_seek(
        self,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
    ) -> None:
        """On `SeekHook`, `PostRunArmedHook` record where to next take data"""
        # Skip the uid so it is guaranteed to be unique
        self._uid_offset += self._completed_steps + self._steps_to_do - completed_steps
        self._completed_steps = completed_steps
        self._steps_to_do = steps_to_do

    @add_call_types
    def on_reset(self) -> None:
        """On `AbortHook`, `ResetHook` close HDF file if it exists"""
        if self._hdf:
            self._hdf.close()
            self._hdf = None

    def _create_infos(self, detector_name, filename):
        # Main dataset
        yield scanning.infos.DatasetProducedInfo(
            name="%s.data" % detector_name,
            filename=filename,
            type=scanning.util.DatasetType.PRIMARY,
            rank=len(self._generator.shape) + 2,
            path=DATA_PATH,
            uniqueid=UID_PATH,
        )
        # Sum
        yield scanning.infos.DatasetProducedInfo(
            name="%s.sum" % detector_name,
            filename=filename,
            type=scanning.util.DatasetType.SECONDARY,
            rank=len(self._generator.shape) + 2,
            path=SUM_PATH,
            uniqueid=UID_PATH,
        )
        # Add an axis for each setpoint
        for dim in self._generator.axes:
            yield scanning.infos.DatasetProducedInfo(
                name="%s.value_set" % dim,
                filename=filename,
                type=scanning.util.DatasetType.POSITION_SET,
                rank=1,
                path=SET_PATH % dim,
                uniqueid="",
            )

    def _create_hdf(self, filepath: str) -> h5py.File:
        # The generator tells us what dimensions our scan should be. The dataset
        # will grow, so start off with the smallest we need
        initial_shape = tuple(1 for _ in self._generator.shape)
        # Open the file with the latest libver so SWMR works
        hdf = h5py.File(filepath, "w", libver="latest")
        # Write the datasets
        # The detector dataset containing the simulated data
        hdf.create_dataset(
            DATA_PATH,
            dtype=np.uint8,
            shape=initial_shape + (self._height, self._width),
            maxshape=self._generator.shape + (self._height, self._width),
        )
        # Make the scalar datasets
        for path, dtype in {UID_PATH: np.int32, SUM_PATH: np.float64}.items():
            hdf.create_dataset(
                path,
                dtype=dtype,
                shape=initial_shape + (1, 1),
                maxshape=self._generator.shape + (1, 1),
            )
        # Make the setpoint dataset
        for d in self._generator.dimensions:
            for axis in d.axes:
                # Make a data set for the axes, holding an array holding
                # floating point data, for each point specified in the generator
                ds = hdf.create_dataset(SET_PATH % axis, data=d.get_positions(axis))
                ds.attrs["units"] = self._generator.units[axis]
        # Datasets made, we can switch to SWMR mode now
        hdf.swmr_mode = True
        return hdf

    def _write_data(self, point: Point, step: int) -> None:
        point_needs_shape = tuple(x + 1 for x in point.indexes) + (1, 1)
        # Resize the datasets so they fit
        for path in (DATA_PATH, SUM_PATH, UID_PATH):
            ds = self._hdf[path]
            expand_to = tuple(max(*z) for z in zip(point_needs_shape, ds.shape))
            ds.resize(expand_to)
        # Write the detector data, multiply by exposure / duration to allow us
        # to make dimmer images by reducint exposure relative to other detectors
        intensity = interesting_pattern(point) * self._exposure / point.duration
        detector_data = (self._blob * intensity).astype(np.uint8)
        index = tuple(point.indexes)
        self._hdf[DATA_PATH][index] = detector_data
        self._hdf[SUM_PATH][index] = np.sum(detector_data)
        self._hdf[UID_PATH][index] = step + self._uid_offset + 1

    def _flush_datasets(self):
        # Note that UID comes last so anyone monitoring knows the data is there
        for path in (DATA_PATH, SUM_PATH, UID_PATH):
            self._hdf[path].flush()
