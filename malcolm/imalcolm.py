#!/bin/env dls-python

import collections
import signal
import sys
import os
import threading

# Start qt
def start_qt():
    from PyQt4.Qt import QApplication
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.exec_()

qt_thread = threading.Thread(target=start_qt)
qt_thread.start()


def make_process():
    import argparse
    import logging

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
        help="The YAML file containing the blocks to be loaded"
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
    from malcolm.yamlutil import make_include_creator

    sf = SyncFactory("Sync")

    from malcolm.gui.blockgui import BlockGui

    guis = {}

    def gui(block):
        if block in guis:
            guis[block].show()
        else:
            guis[block] = BlockGui(proc, block)
        return guis[block]

    if args.yaml:
        proc_name = os.path.basename(args.yaml).split(".")[-2]
        proc = Process(proc_name, sf)
        with open(args.yaml) as f:
            assembly = make_include_creator(f.read())
        assembly(proc, {})
        proc_name = "%s - imalcolm" % proc_name
    else:
        proc = Process("Process", sf)
        proc_name = "imalcolm"
    # set terminal title
    sys.stdout.write("\x1b]0;%s\x07" % proc_name)

    if args.client:
        if args.client.startswith("ws://"):
            from malcolm.comms.websocket import WebsocketClientComms
            hostname, port = args.client[5:].split(":")
            comms = WebsocketClientComms(
                proc, dict(hostname=hostname, port=int(port)))
            proc.add_comms(comms)
        else:
            raise ValueError(
                "Don't know how to create client to %s" % args.client)

    return proc, gui


def main():
    self, gui = make_process()
    sampler = Sampler()

    header = """Welcome to iMalcolm.

self.process_block.blocks:
    %s

Try:
hello = self.get_block("hello")
print hello.greet("me")

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


class Sampler(object):
    def __init__(self, interval=0.1):
        self.stack_counts = collections.defaultdict(int)
        self.interval = interval

    def _sample(self, signum, frame):
        for frame in sys._current_frames().values():
            stack = []
            while frame is not None:
                formatted_frame = '{}({})'.format(
                    frame.f_code.co_name, frame.f_globals.get('__name__'))
                stack.append(formatted_frame)
                frame = frame.f_back

            formatted_stack = ';'.join(reversed(stack))
            self.stack_counts[formatted_stack] += 1
        signal.setitimer(signal.ITIMER_VIRTUAL, self.interval, 0)

    def start(self):
        signal.signal(signal.SIGVTALRM, self._sample)
        signal.setitimer(signal.ITIMER_VIRTUAL, self.interval, 0)

if __name__ == "__main__":
    # Test
    from pkg_resources import require

    require("tornado", "numpy", "cothread", "ruamel.yaml",
            "scanpointgenerator")
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scanpointgenerator"))
    sys.path.append(
        "/dls_sw/work/R3.14.12.3/support/pvaPy/lib/python/2.7/linux-x86_64")
    main()
