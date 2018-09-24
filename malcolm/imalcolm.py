#!/dls_sw/prod/tools/RHEL6-x86_64/defaults/bin/dls-python


def make_async_logging(log_config):
    # Now we have our user specified logging config, pipe all logging messages
    # through a queue to make it asynchronous
    from malcolm.compat import QueueListener, queue
    import logging.config

    # These are the handlers for our root logger, they should go through a queue
    root_handlers = log_config["root"].pop("handlers")

    # Create a new handler to replace all the above that just pops messages on
    # a queue, and set it as the handler for the root logger (and children)
    q = queue.Queue()
    log_config["handlers"]["queue"] = {
        "class": "malcolm.compat.QueueHandler", "queue": q}
    log_config["root"]["handlers"] = ["queue"]
    logging.config.dictConfig(log_config)

    # Now make a queue listener that consumes messages on the queue and forwards
    # them to any of the appropriate original root handlers
    handlers = [logging._handlers[h] for h in root_handlers]
    listener = QueueListener(q, *handlers, respect_handler_level=True)
    return listener


def make_process():
    import sys
    import threading
    import argparse
    import atexit
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
                "format": "%(name)s: %(message)s"
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

            "local_file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "extended",
                "filename": "/tmp/malcolm-debug.log",
                "maxBytes": 100048576,
                "backupCount": 4,
                "encoding": "utf8"
            },

            "graylog_gelf": {
                "class": "pygelf.GelfTcpHandler",
                # Obviously a DLS-specific configuration: the graylog server
                # address and port
                "host": "graylog2.diamond.ac.uk",
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
            "handlers": ["graylog_gelf", "console", "local_file_handler"],
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

    # Start it off, and tell it to stop when we quit
    listener = make_async_logging(log_config)
    listener.start()
    atexit.register(listener.stop)

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
        locals_d["profiler"].start()

    from malcolm.core import Context, Queue, Process
    from malcolm.modules.builtin.blocks import proxy_block
    from malcolm.yamlutil import make_include_creator

    if args.yaml:
        proc_name = os.path.basename(args.yaml).split(".")[-2]
        proc = Process(proc_name)
        controllers, parts = make_include_creator(args.yaml)()
        assert not parts, "%s defines parts" % (args.yaml,)
        for controller in controllers:
            proc.add_controller(controller)
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
            comms = WebsocketClientComms(
                mri="%s:%s" % (hostname, port), hostname=hostname,
                port=int(port))
        elif args.client == "pva":
            from malcolm.modules.pva.controllers import PvaClientComms
            comms = PvaClientComms(mri="pva")
        else:
            raise ValueError(
                "Don't know how to create client to %s" % args.client)
        proc.add_controller(comms)

    class UserContext(Context):
        def make_queue(self):
            return Queue(user_facing=True)

        def post(self, path, params=None, timeout=None):
            try:
                return super(UserContext, self).post(path, params, timeout)
            except KeyboardInterrupt:
                self.post([path[0], "abort"])
                raise

        def make_proxy(self, comms, mri):
            proc.add_controller(proxy_block(comms=comms, mri=mri)[-1])

    locals_d["self"] = UserContext(proc)
    proc.start(timeout=60)
    locals_d["process"] = proc
    return locals_d


def main():
    locals_d = make_process()

    header = """Welcome to iMalcolm.

self.mri_list:
    %s

Try:
hello = self.block_view("HELLO")
hello.greet("me")

or

gui(self.block_view("COUNTER"))

or

self.make_proxy("localhost:8008", "HELLO")
self.block_view("HELLO").greet("me")
""" % (locals_d["self"].mri_list,)

    try:
        import IPython
    except ImportError:
        import code
        code.interact(header, local=locals_d)
    else:
        locals().update(locals_d)
        IPython.embed(header=header)
    if "profiler" in locals_d:
        if locals_d["profiler"].started:
            locals_d["profiler"].stop()
    # TODO: tearDown doesn't work properly yet
    # locals_d["process"].stop()


if __name__ == "__main__":
    print("Loading...")
    import os
    import sys

    os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "6000000"

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    from pkg_resources import require

    require("tornado", "numpy", "ruamel.yaml", "cothread==2.14", "vdsgen~=0.3",
            "pygelf==0.3.1", "scanpointgenerator==2.1.1", "plop", "h5py~=2.8",
            "annotypes>=0.9")
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "cothread"))
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "annotypes"))
    sys.path.append(
        "/dls_sw/work/R3.14.12.3/support/pvaPy/lib/python/2.7/linux-x86_64")

    main()
