#!/bin/env dls-python
import os
import sys
import logging

# Start some logging
#logging.basicConfig(level=logging.DEBUG)

from pkg_resources import require
require("numpy", "ruamel.yaml", "scanpointgenerator", "cothread")
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from malcolm.core import SyncFactory, Process, Task
from malcolm.blocks.demo import SimulatorPMACManager
from scanpointgenerator import LineGenerator, CompoundGenerator, \
    FixedDurationMutator

# Make the top level objects
sf = SyncFactory("Sync")
process = Process("Process", sf)

# Make the malcolm object
params = SimulatorPMACManager.MethodMeta.prepare_input_map(
    mriPrefix="TST-PMAC")
SimulatorPMACManager(process, params)
sim = process.get_block("TST-PMAC")

# Start the process
process.start()

# Wait for everything to settle down
task = Task("waiter", process)
task.when_matches(sim["state"], "Idle", timeout=10)

# Do a test
xs = LineGenerator("m1", "mm", -8., -12., 121, alternate_direction=True)
ys = LineGenerator("m2", "mm", -4., -6., 21)
gen = CompoundGenerator([ys, xs], [], [FixedDurationMutator(0.005)])
for i in range(1):
    sim.configure(gen)
    sim.run()

#process.stop()
