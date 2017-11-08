#!/bin/env dls-python
import os
import sys
import logging
from pkg_resources import require

logging.basicConfig()
require("tornado", "numpy", "cothread")

from malcolm.core import Process, call_with_params
from malcolm.modules.web.controllers import HTTPServerComms
from malcolm.modules.web.parts import WebsocketServerPart
from malcolm.modules.pandablocks.controllers import PandABlocksManagerController
from malcolm.modules.builtin.parts import LabelPart

# Input params
HOSTNAME = "localhost"
PORT = 8888
WSPORT = 8080
CONFIGDIR = "/tmp"
MRI = "PANDABOX"

# Make the top level objects
process = Process("Process")

# Add the websocket server
part = call_with_params(WebsocketServerPart)
controller = call_with_params(
    HTTPServerComms, process, [part], port=WSPORT, mri="WS")
process.add_controller("WS", controller)

# Add the PandABox
label = call_with_params(LabelPart, initialValue="PandABox")
controller = call_with_params(
    PandABlocksManagerController, process, [label],
    configDir=CONFIGDIR, hostname=HOSTNAME, port=PORT, mri=MRI)
process.add_controller(MRI, controller)

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
header = "Welcome to PandABox"
try:
    import IPython
except ImportError:
    import code
    code.interact(header, local=locals())
else:
    IPython.embed(header=header)

# TODO: why does this not shutdown cleanly? socket.shutdown not called right?
process.stop(timeout=1)
