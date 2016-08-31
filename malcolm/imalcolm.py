#!/bin/env dls-python

def make_process():
    import argparse
    import logging
    import cothread

    cothread.iqt()
    cothread.input_hook._qapp.setQuitOnLastWindowClosed(False)

    parser = argparse.ArgumentParser(
        description="Interactive shell for malcolm")
    parser.add_argument(
        '--client', '-c',
        help="Add a client to given server, like ws://localhost:8080 or pva")
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

    from malcolm.core import SyncFactory, Process
    from malcolm.assemblyutil import make_assembly
    from malcolm.gui.blockgui import BlockGui

    proc = Process("Process", SyncFactory("Sync"))
    guis = {}

    if args.yaml:
        with open(args.yaml) as f:
            assembly = make_assembly(f.read())
        assembly(proc, {})

    def gui(block):
        if block in guis:
            guis[block].show()
        else:
            guis[block] = BlockGui(proc, block)
        return guis[block]

    if args.client:
        if args.client.startswith("ws://"):
            from malcolm.comms.websocket import WebsocketClientComms
            hostname, port = args.client[5:].split(":")
            WebsocketClientComms(proc, dict(hostname=hostname, port=int(port)))
        else:
            raise ValueError(
                "Don't know how to create client to %s" % args.client)

    return proc, gui


def main():
    self, gui = make_process()

    header = """Welcome to iMalcolm.

self.process_block.blocks:
    %s

Try:
hello = self.get_block("hello")
print hello.say_hello("me")

or

gui(self.get_block("counter"))

or

self.process_block.blocks
""" % self.process_block.blocks

    self.start()
    try:
        import IPython
    except ImportError:
        import code
        code.interact(header, local=locals())
    else:
        IPython.embed(header=header)

if __name__ == "__main__":
    # Test
    import os
    import sys
    from pkg_resources import require

    require("tornado", "numpy", "cothread", "ruamel.yaml",
            "scanpointgenerator")
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.append(
        "/dls_sw/work/R3.14.12.3/support/pvaPy/lib/python/2.7/linux-x86_64")
    main()
