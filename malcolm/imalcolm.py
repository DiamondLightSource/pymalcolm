#!/bin/env dls-python
import argparse
import logging
import sys
import os

if __name__ == "__main__":
    # Test
    from pkg_resources import require
    require("tornado", "numpy", "cothread", "ruamel.yaml")  # noqa
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..",
                                 "scanpointgenerator"))

from PyQt4.Qt import QApplication

from malcolm.core import SyncFactory, Process
from malcolm.controllers import ClientController
from malcolm.comms.websocket import WebsocketServerComms, WebsocketClientComms
from malcolm.gui.blockgui import BlockGui
from malcolm.assemblyutil import make_assembly

# TODO: merge this into Process
class IMalcolm(object):
    def __init__(self, yaml=None):
        self.client_comms = []
        self.server_comms = []
        self.sync_factory = SyncFactory("Sync")
        self.process = Process("Process", self.sync_factory)
        if yaml:
            with open(yaml) as f:
                assembly = make_assembly(f.read())
            assembly(self.process, {})

    def add_client_comms(self, url):
        assert url.startswith("ws://"), "Can only do websockets"
        cc = WebsocketClientComms(url, self.process, url)
        self.client_comms.append(cc)
        return cc

    def add_server_comms(self, url):
        #assert url.startswith("ws://"), "Can only do websockets"
        ss = WebsocketServerComms(url, self.process, url)
        self.server_comms.append(ss)
        return ss

    def start(self):
        self.process.start()
        for sc in self.server_comms:
            sc.start()
        for cc in self.client_comms:
            cc.start()

    def stop(self):
        for cc in self.client_comms:
            cc.stop()
        for sc in self.server_comms:
            sc.stop()
        self.process.stop()

    def get_block(self, block_name):
        return self.process._blocks[block_name]

    def make_client(self, block_name):
        controller = ClientController(block_name, self.process)
        return controller.block

    def gui(self, block_name):
        if not hasattr(self, "app"):
            self.app = QApplication(sys.argv)
        gui = BlockGui(self.process, block_name)
        self.app.exec_()
        return gui


def make_imalcolm():
    parser = argparse.ArgumentParser(
        description="Interactive shell for malcolm")
    parser.add_argument(
        '--client', '-c',
        help="Add a client to given server, like ws://172.23.243.13:5600")
    parser.add_argument(
        '--server', '-s',
        help="Start a server with the given string, like ws://0.0.0.0:5600")
    parser.add_argument(
        '--log', default="INFO",
        help="Lowest level of logs to see. One of: ERROR, WARNING, INFO, DEBUG "
        "Default is INFO")
    parser.add_argument(
        'yaml', nargs="?",
        help="The YAML file containing the assemblies to be loaded"
    )
    args = parser.parse_args()
    # assuming loglevel is bound to the string value obtained from the
    # command line argument. Convert to upper case to allow the user to
    # specify --log=DEBUG or --log=debug
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log)
    logging.basicConfig(level=numeric_level)

    im = IMalcolm(args.yaml)
    if args.client:
        im.add_client_comms(args.client)
    if args.server:
        im.add_server_comms(args.server)
    return im


def main():
    self = make_imalcolm()
    self.start()

    header = """Welcome to iMalcolm.

Try:
hello = self.get_block("hello")
print hello.say_hello("me")

or

self.gui(self.make_client("counter"))
"""
    try:
        import IPython
    except ImportError:
        import code
        code.interact(header, local=locals())
    else:
        IPython.embed(header=header)

if __name__ == "__main__":
    # Entry point
    main()
