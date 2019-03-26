import os
import time

import h5py
import numpy as np
from annotypes import add_call_types, Anno
from scanpointgenerator import Point

from malcolm.core import Part, APartName, PartRegistrar
from malcolm.modules import builtin, scanning
from malcolm.modules.scanning.infos import DatasetProducedInfo
from malcolm.modules.scanning.util import DatasetType

with Anno("Width of detector image"):
    AWidth = int
with Anno("Height of detector image"):
    AHeight = int


# Datasets where we will write our data
DATA_PATH = "/entry/data"
SUM_PATH = "/entry/sum"
UID_PATH = "/entry/uid"

# How often we flush in seconds
FLUSH_PERIOD = 1

def make_gaussian_blob(width, height):
    x, y = np.meshgrid(np.linspace(-1, 1, width), np.linspace(-1, 1, height))
    d = np.sqrt(x*x+y*y)
    blob = np.exp(-d**2)
    return blob


def interesting_pattern(point):
    # type: (Point) -> float
    # Grab the x and y values out of the point
    x = [v for k, v in sorted(point.positions.items()) if "x" in k.lower()][0]
    y = [v for k, v in sorted(point.positions.items()) if "y" in k.lower()][0]
    # Return a value between 0 and 1 based on a function that gives interesting
    # pattern on x and y in range -10:10
    z = 0.5 + (np.sin(x)**10 + np.cos(10 + y*x) * np.cos(x))/2
    return z


class FileWritePart(Part):
    """Minimal interface demonstrating a file writing detector part"""
    def __init__(self, name, width=320, height=240):
        # type: (APartName, AWidth, AHeight) -> None
        super(FileWritePart, self).__init__(name)
        # Store input arguments
        self.width = width
        self.height = height
        # The detector image we will modify for each image (0..255 range)
        self.blob = make_gaussian_blob(width, height) * 255
        # The hdf file we will write
        self.hdf = None  # type: h5py.File
        # Configure args and progress info
        self.generator = None  # type: scanning.hooks.AGenerator
        self.completed_steps = 0
        self.steps_to_do = 0
        # How much to offset uid value from generator point
        self.uid_offset = 0
        # Hooks
        self.register_hooked(scanning.hooks.ConfigureHook, self.configure)
        self.register_hooked((scanning.hooks.PostRunArmedHook,
                              scanning.hooks.SeekHook), self.seek)
        self.register_hooked((scanning.hooks.RunHook,
                              scanning.hooks.ResumeHook), self.run)
        self.register_hooked((scanning.hooks.AbortHook,
                              builtin.hooks.ResetHook), self.reset)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(FileWritePart, self).setup(registrar)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    @add_call_types
    def reset(self):
        # type: () -> None
        if self.hdf:
            self.hdf.close()
            self.hdf = None

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: scanning.util.AFileDir
                  formatName="det",  # type: scanning.util.AFormatName
                  fileTemplate="%s.h5",  # type: scanning.util.AFileTemplate
                  ):
        # type: (...) -> scanning.hooks.UInfos
        # Store args
        self.completed_steps = completed_steps
        self.steps_to_do = steps_to_do
        self.generator = generator
        self.uid_offset = 0
        # Work out where to write the file
        filename = fileTemplate % formatName
        filepath = os.path.join(fileDir, filename)
        # The generator tells us what dimensions our scan should be. The dataset
        # will grow, so start off with the smallest we need
        initial_shape = tuple(1 for _ in generator.shape)
        # Write the initial dataset structure
        with h5py.File(filepath, "w", libver="latest") as hdf:
            # The detector dataset containing the simulated data
            hdf.create_dataset(
                DATA_PATH, dtype=np.uint8,
                shape=initial_shape + (self.height, self.width),
                maxshape=generator.shape + (self.height, self.width))
            # Make the scalar datasets
            for path, dtype in {UID_PATH: np.int32, SUM_PATH: np.float64}:
                hdf.create_dataset(
                    path, dtype=dtype,
                    shape=initial_shape + (1, 1),
                    maxshape=generator.shape + (1, 1))
        # Re-open the file in swmr mode
        self.hdf = h5py.File(filepath, "a", libver="latest", swmr=True)
        # Tell everyone what we're going to make
        infos = [
            # Main dataset
            DatasetProducedInfo(
                name="%s.data" % formatName,
                filename=filename,
                type=DatasetType.PRIMARY,
                rank=len(generator.shape) + 2,
                path=DATA_PATH,
                uniqueid=UID_PATH),
            # Sum
            DatasetProducedInfo(
                name="%s.sum" % formatName,
                filename=filename,
                type=DatasetType.SECONDARY,
                rank=len(generator.shape) + 2,
                path=SUM_PATH,
                uniqueid=UID_PATH)]
        return infos

    @add_call_types
    def seek(self,
             completed_steps,  # type: scanning.hooks.ACompletedSteps
             steps_to_do,  # type: scanning.hooks.AStepsToDo
             ):
        # type: (...) -> None
        # Skip the uid so it is guaranteed to be unique
        self.uid_offset = completed_steps - (
                self.completed_steps + self.steps_to_do)
        self.completed_steps = completed_steps
        self.steps_to_do = steps_to_do

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Start time so everything is relative
        point_time = time.time()
        last_flush = point_time
        for i in range(self.completed_steps,
                       self.completed_steps + self.steps_to_do):
            self.log.debug("Starting point %s", i)
            # Get the point we are meant to be scanning
            point = self._generator.get_point(i)
            self._write_data(point, i)
            # Flush the datasets if it is time to
            if time.time() - last_flush > FLUSH_PERIOD:
                last_flush = time.time()
                self._flush_datasets()
            # Wait until the next point is due
            point_time += point.duration
            wait_time = point_time - time.time()
            self.log.debug("%s Sleeping %s", self.name, wait_time)
            context.sleep(wait_time)
            # Update the point as being complete
            self.registrar.report(scanning.infos.RunProgressInfo(i + 1))
        # Do one last flush and then we're done
        self._flush_datasets()

    def _write_data(self, point, step):
        # type: (Point, int) -> None
        point_needs_shape = tuple(point.indexes) + (1, 1)
        # Resize the datasets so they fit
        for path in (DATA_PATH, SUM_PATH, UID_PATH):
            ds = self.hdf[path]
            expand_to = tuple(max(*z) for z in zip(point_needs_shape, ds.shape))
            ds.resize(expand_to)
        # Write the detector data
        intensity = interesting_pattern(point)
        detector_data = (self.blob * intensity).astype(np.uint8)
        self.hdf[DATA_PATH][point.indexes] = detector_data
        self.hdf[SUM_PATH][point.indexes] = np.sum(detector_data)
        self.hdf[UID_PATH][point.indexes] = step + self.uid_offset + 1

    def _flush_datasets(self):
        # Note that UID comes last so anyone monitoring knows the data is there
        for path in (DATA_PATH, SUM_PATH, UID_PATH):
            self.hdf[path].flush()












