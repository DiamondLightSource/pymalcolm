#!/bin/env dls-python
import os
import sys

from pkg_resources import require
require("tornado", "numpy")
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from malcolm.core import SyncFactory, Process
from malcolm.controllers import ManagerController
from malcolm.comms.websocket.websocketservercomms import WebsocketServerComms
from malcolm.includes.pandabox.hardware_collection import hardware_collection

# Input params
HOSTNAME = "localhost"
PORT = 8888
WSPORT = 8080

# Make the top level objects
sf = SyncFactory("Sync")
process = Process("Process", sf)

# Add the websocket server
params = WebsocketServerComms.MethodMeta.prepare_input_map(port=WSPORT)
comms = WebsocketServerComms(process, params)
process.add_comms(comms)

# We daemonise the server by double forking, but we leave the controlling
# terminal and other file connections alone.
if False and os.fork():
    # Exit first parent
    sys.exit(0)
# Do second fork to avoid generating zombies
if False and os.fork():
    sys.exit(0)

# Make the parts by querying the PandABox
params = hardware_collection.MethodMeta.prepare_input_map(
    mriPrefix="P", hostname=HOSTNAME, port=PORT)
_, parts = hardware_collection(process, params)

# Make a controller for the top level
params = ManagerController.MethodMeta.prepare_input_map(
    mri="P", configDir="/tmp")
controller = ManagerController(process, parts, params)

# Start the server
for comms in process.comms:
    comms.start()
process.recv_loop()
