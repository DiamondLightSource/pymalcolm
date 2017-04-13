#!/dls_sw/prod/tools/RHEL6-x86_64/defaults/bin/dls-python

def make_process():
    import sys
    import threading
    import argparse
    import logging
    from os import environ

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

    def gui(block):
        global opener
        opener.open_gui(block, proc)

    try:
        environ['DISPLAY']
        # If this environment variable doesn't exist then there is probably no
        # X server for us to talk to.
    except KeyError:
        qt_thread = None
    else:
        from PyQt4.Qt import QApplication

        # Start qt
        def start_qt():
            global app
            app = QApplication(sys.argv)
            app.setQuitOnLastWindowClosed(False)
            from malcolm.gui.guiopener import GuiOpener
            global opener
            opener = GuiOpener()
            app.exec_()

        qt_thread = threading.Thread(target=start_qt)

    from malcolm.core import Process, call_with_params, Context
    from malcolm.yamlutil import make_include_creator

    if args.yaml:
        proc_name = os.path.basename(args.yaml).split(".")[-2]
        proc = Process(proc_name)
        assembly = make_include_creator(args.yaml)
        call_with_params(assembly, proc)
        proc_name = "%s - imalcolm" % proc_name
    else:
        proc = Process("Process")
        proc_name = "imalcolm"
    # set terminal title
    sys.stdout.write("\x1b]0;%s\x07" % proc_name)

    if args.client:
        if args.client.startswith("ws://"):
            from malcolm.controllers.web import WebsocketClientComms
            hostname, port = args.client[5:].split(":")
            comms = call_with_params(
                WebsocketClientComms, proc, mri=hostname, hostname=hostname,
                port=int(port))
            proc.add_controller(comms.mri, comms)
        else:
            raise ValueError(
                "Don't know how to create client to %s" % args.client)

    context = Context("IMalcolmContext", proc)
    if qt_thread:
        qt_thread.start()
    proc.start()
    return context, gui


def main():
    self, gui = make_process()

    header = """Welcome to iMalcolm.

self.mri_list:
    %s

Try:
hello_block = self.block_view("HELLO")
print hello_block.greet("me")

or

gui(self.block_view("COUNTER"))

""" % (self.mri_list,)

    try:
        import IPython
    except ImportError:
        import code
        code.interact(header, local=locals())
    else:
        IPython.embed(header=header)
    global app
    app.quit()


if __name__ == "__main__":
    import os
    import sys

    os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "6000000"

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    from pkg_resources import require

    require("tornado", "numpy", "cothread", "ruamel.yaml",
            "scanpointgenerator")
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scanpointgenerator"))
    sys.path.append(
        "/dls_sw/work/R3.14.12.3/support/pvaPy/lib/python/2.7/linux-x86_64")

    main()
