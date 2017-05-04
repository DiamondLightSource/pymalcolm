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

    # These are the locals that we will pass to the console
    locals_d = {}

    parser = argparse.ArgumentParser(
        description="Interactive shell for malcolm")
    parser.add_argument(
        '--client', '-c',
        help="Add a client to given server, like ws://localhost:8080 or pva")
    parser.add_argument(
        '--logcfg', help="Logging dict config in JSON or YAML file")
    parser.add_argument(
        "--profiledir", help="Directory to store profiler results in",
        default="/tmp/imalcolm_profiles")
    parser.add_argument(
        'yaml', nargs="?",
        help="The YAML file containing the blocks to be loaded")
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

    # Setup Qt gui, must be done before any malcolm imports otherwise cothread
    # starts in the wrong thread
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
            app = QApplication(sys.argv)
            app.setQuitOnLastWindowClosed(False)
            locals_d["app"] = app
            from malcolm.gui.guiopener import GuiOpener
            global opener
            opener = GuiOpener()
            app.exec_()

        qt_thread = threading.Thread(target=start_qt)

        def gui(block):
            global opener
            opener.open_gui(block, proc)

        locals_d["gui"] = gui

    # Setup profiler dir
    try:
        from malcolm.modules.profiling.parts import ProfilingViewerPart
        from malcolm.modules.profiling.profiler import Profiler
    except ImportError:
        raise
    else:
        if not os.path.isdir(args.profiledir):
            os.mkdir(args.profiledir)
        ProfilingViewerPart.profiledir = args.profiledir
        locals_d["profiler"] = Profiler(args.profiledir)
        #locals_d["profiler"].start()

    from malcolm.core import Process, call_with_params, Context
    from malcolm.modules.builtin.blocks import proxy_block
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
                WebsocketClientComms, proc, [],
                mri="%s:%s" % (hostname, port), hostname=hostname,
                port=int(port))
            proc.add_controller(comms.mri, comms)
        else:
            raise ValueError(
                "Don't know how to create client to %s" % args.client)

    class UserContext(Context):
        def post(self, path, params=None, timeout=None):
            try:
                return super(UserContext, self).post(path, params, timeout)
            except KeyboardInterrupt:
                self.post([path[0], "abort"])
                raise

        def make_proxy(self, comms, mri):
            call_with_params(proxy_block, proc, comms=comms, mri=mri)

    locals_d["self"] = UserContext(proc, user_facing=True)
    if qt_thread:
        qt_thread.start()
    proc.start()
    locals_d["process"] = proc
    return locals_d


def main():
    locals_d = make_process()

    header = """Welcome to iMalcolm.

self.mri_list:
    %s

Try:
hello = self.block_view("HELLO")
print hello.greet("me")

or

gui(self.block_view("COUNTER"))

or

self.make_proxy("localhost:8080", "HELLO")
print self.block_view("HELLO").greet("me")
""" % (locals_d["self"].mri_list,)

    try:
        import IPython
    except ImportError:
        import code
        code.interact(header, local=locals_d)
    else:
        locals().update(locals_d)
        IPython.embed(header=header)
    if "app" in locals_d:
        locals_d["app"].quit()
    if "profiler" in locals_d:
        if locals_d["profiler"].started:
            locals_d["profiler"].stop()
    # TODO: tearDown doesn't work properly yet
    # locals_d["process"].stop()


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
