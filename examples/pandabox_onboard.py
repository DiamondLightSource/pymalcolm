#!/bin/env dls-python
import os
import sys
import code

from pkg_resources import require

require("tornado", "numpy")
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from malcolm.core import Process, call_with_params
from malcolm.modules.web.controllers import HTTPServerComms
from malcolm.modules.web.parts import WebsocketServerPart
from malcolm.modules.pandablocks.controllers import PandABlocksManagerController

# Input params
HOSTNAME = "localhost"
PORT = 8888
WSPORT = 8080
CONFIGDIR = "/tmp"

# Make the top level objects
process = Process("Process")

# Add the websocket server
part = call_with_params(WebsocketServerPart)
controller = call_with_params(
    HTTPServerComms, process, [part], port=WSPORT, mri="WS")
process.add_controller("WS", controller)

# Add the PandABox
controller = call_with_params(
    PandABlocksManagerController, process, [],
    configDir=CONFIGDIR, hostname=HOSTNAME, port=PORT, mri="P")
process.add_controller("P", controller)

# We daemonise the server by double forking, but we leave the controlling
# terminal and other file connections alone.
# Not working until we defer cothread import until later...
if False:
    if os.fork():
        # Exit first parent
        sys.exit(0)
    # Do second fork to avoid generating zombies
    if os.fork():
        sys.exit(0)

# Start the server
process.start()

# Wait for completion
code.interact("Welcome to PandABox", local=locals())

# TODO: why does this not shutdown cleanly? socket.shutdown not called right?
process.stop()
