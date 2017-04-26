#!/dls_sw/prod/tools/RHEL6-x86_64/defaults/bin/dls-python

def make_process():
    import sys
    import threading
    import argparse
    import logging.config
    import os
    import getpass
    import json
    from ruamel import yaml

    parser = argparse.ArgumentParser(
        description="Interactive shell for malcolm")
    parser.add_argument(
        '--client', '-c',
        help="Add a client to given server, like ws://localhost:8080 or pva")
    parser.add_argument(
        '--logcfg', help="Logging dict config in JSON or YAML file")
    parser.add_argument(
        'yaml', nargs="?",
        help="The YAML file containing the blocks to be loaded"
    )
    args = parser.parse_args()

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "simple": {
                "format": "%(message)s"
            },
            "extended": {
                "format": "%(asctime)s - %(levelname)6s - %(name)s\n"
                          "    %(message)s"
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },

            # "local_file_handler": {
            #     "class": "logging.handlers.RotatingFileHandler",
            #     "level": "DEBUG",
            #     "formatter": "extended",
            #     "filename": "debug.log",
            #     "maxBytes": 1048576,
            #     "backupCount": 20,
            #     "encoding": "utf8"
            # },

            "graylog_gelf": {
                "class": "pygelf.GelfUdpHandler",
                # Obviously a DLS-specific configuration: the graylog server
                # address and port
                "host": "cs04r-sc-serv-14.diamond.ac.uk",
                "port": 12202,
                "debug": True,
                "level": "DEBUG",
                #  The following custom fields will be disabled if setting this
                # False
                "include_extra_fields": True,
                "username": getpass.getuser(),
                "pid": os.getpid()
            }
        },


        # "loggers": {
        #     # Fine-grained logging configuration for individual modules or
        #     # classes
        #     # Use this to set different log levels without changing 'real' code.
        #     "myclasses": {
        #         "level": "DEBUG",
        #         "propagate": True
        #     },
        #     "usermessages": {
        #         "level": "INFO",
        #         "propagate": True,
        #         "handlers": ["console"]
        #     }
        # },

        "root": {
            "level": "DEBUG",
            "handlers": ["graylog_gelf", "console"],
        }
    }

    if args.logcfg:
        with open(args.logcfg) as f:
            text = f.read()
        if args.logcfg.endswith(".json"):
            file_config = json.loads(text)
        else:
            file_config = yaml.load(text, Loader=yaml.RoundTripLoader)
        if file_config:
            log_config = file_config
    logging.config.dictConfig(log_config)

    from pygelf import GelfUdpHandler

    def gui(block):
        global opener
        opener.open_gui(block, proc)

    try:
        os.environ['DISPLAY']
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
            from malcolm.modules.web.controllers import WebsocketClientComms
            hostname, port = args.client[5:].split(":")
            comms = call_with_params(
                WebsocketClientComms, proc, mri=hostname, hostname=hostname,
                port=int(port))
            proc.add_controller(comms.mri, comms)
        else:
            raise ValueError(
                "Don't know how to create client to %s" % args.client)

    context = Context(proc)
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
    print "Loading..."
    import os
    import sys

    os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "6000000"

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    from pkg_resources import require

    require("tornado", "numpy", "cothread", "ruamel.yaml",
            "scanpointgenerator", "plop", "pygelf")
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scanpointgenerator"))
    sys.path.append(
        "/dls_sw/work/R3.14.12.3/support/pvaPy/lib/python/2.7/linux-x86_64")

    main()
