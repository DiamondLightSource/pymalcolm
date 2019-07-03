#!/dls_sw/prod/tools/RHEL7-x86_64/defaults/bin/dls-python
import logging.config
import threading
import argparse
import atexit
import getpass
import json
import os
import sys


def make_async_logging(log_config):
    from malcolm.compat import QueueListener, queue
    # Now we have our user specified logging config, pipe all logging messages
    # through a queue to make it asynchronous

    # These are the handlers for our root logger, they should go through a queue
    root_handlers = log_config["root"].pop("handlers")

    # Create a new handler to replace all the above that just pops messages on
    # a queue, and set it as the handler for the root logger (and children)
    q = queue.Queue()
    log_config["handlers"]["queue"] = {
        "class": "malcolm.compat.QueueHandler", "queue": q}
    log_config["root"]["handlers"] = ["queue"]
    configurator = logging.config.DictConfigurator(log_config)
    configurator.configure()

    # Our handlers can be got from the converted config dict
    handlers = [configurator.config["handlers"][h] for h in root_handlers]

    # Now make a queue listener that consumes messages on the queue and forwards
    # them to any of the appropriate original root handlers
    listener = QueueListener(q, *handlers, respect_handler_level=True)
    return listener


def parse_args():
    parser = argparse.ArgumentParser(
        description="Interactive shell for malcolm")
    parser.add_argument(
        '--client', '-c',
        help="Add a client to given server, like ws://localhost:8008 or pva")
    parser.add_argument(
        '--logcfg', help="Logging dict config in JSON or YAML file")
    parser.add_argument(
        'yaml', nargs="?",
        help="The YAML file containing the blocks to be loaded")
    args = parser.parse_args()
    return args


def make_logging_config(args):
    from ruamel import yaml

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

            #"local_file_handler": {
            #    "class": "logging.handlers.RotatingFileHandler",
            #    "level": "DEBUG",
            #    "formatter": "extended",
            #    "filename": "/tmp/malcolm-debug.log",
            #    "maxBytes": 100048576,
            #    "backupCount": 4,
            #    "encoding": "utf8"
            #},

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
    return log_config


def prepare_locals(args):
    from malcolm.core import Process
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
    proc.start(timeout=60)
    return proc


def try_prepare_locals(q, args):
    # This will start cothread in this thread
    import cothread
    cothread.input_hook._install_readline_hook(False)
    try:
        locals_d = prepare_locals(args)
    except Exception as e:
        q.put(e)
        raise
    else:
        q.put(locals_d)
    cothread.WaitForQuit(catch_interrupt=False)


def main():
    print("Loading malcolm...")
    from malcolm.compat import queue
    from malcolm.profiler import Profiler

    args = parse_args()

    # Make some log config, either fron command line or
    log_config = make_logging_config(args)

    # Start it off, and tell it to stop when we quit
    listener = make_async_logging(log_config)
    listener.start()
    atexit.register(listener.stop)

    # Setup profiler dir
    profiler = Profiler()
    # profiler.start()

    # If using p4p then set cothread to use the right ca libs before it is
    try:
        import epicscorelibs.path.cothread
    except ImportError:
        pass

    # Import the Malcolm process
    q = queue.Queue()
    t = threading.Thread(target=try_prepare_locals, args=(q, args))
    t.start()
    process = q.get(timeout=65)
    if isinstance(process, Exception):
        # Startup failed, exit now
        sys.exit(1)

    # Now its safe to import Malcolm and cothread
    import cothread

    from malcolm.core import Context
    from malcolm.modules.builtin.blocks import proxy_block

    # Make a user context
    class UserContext(Context):
        def post(self, path, params=None, timeout=None, event_timeout=None):
            try:
                return super(UserContext, self).post(
                    path, params, timeout, event_timeout)
            except KeyboardInterrupt:
                self.post([path[0], "abort"])

        def _make_proxy(self, comms, mri):
            self._process.add_controller(proxy_block(comms=comms, mri=mri)[-1])

        def make_proxy(self, comms, mri):
            # Need to do this in cothread's thread
            cothread.CallbackResult(self._make_proxy, comms, mri)

        def block_view(self, mri):
            return cothread.CallbackResult(
                super(UserContext, self).block_view, mri)

        def make_view(self, controller, data, child_name):
            return cothread.CallbackResult(
                super(UserContext, self).make_view,
                controller, data, child_name)

        def handle_request(self, controller, request):
            cothread.CallbackResult(
                super(UserContext, self).handle_request,
                controller, request)

    self = UserContext(process)

    header = """Welcome to iMalcolm.

self.mri_list:
    %s

# To create a view of an existing Block
block = self.block_view("<mri>")
 
# To create a proxy of a Block in another Malcolm
self.make_proxy("<client_comms_mri>", "<mri>")
block = self.block_view("<mri>")

# To view state of Blocks in a GUI
!firefox localhost:8008""" % (self.mri_list,)

    try:
        import IPython
    except ImportError:
        import code
        code.interact(header, local=locals())
    else:
        IPython.embed(header=header)
    if profiler.running and not profiler.stopping:
        profiler.stop()

    cothread.CallbackResult(process.stop)
    cothread.CallbackResult(cothread.Quit)


if __name__ == "__main__":
    from pkg_resources import require
    print("Loading external modules...")

    os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "6000000"

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    require(
        # External
        "enum34==1.1.6",
        "tornado==4.5.1",
        "numpy==1.13.1",
        "ruamel.yaml==0.15.33",
        "h5py==2.9.0",
        "p4p==3.2.0",
        "pygelf==0.3.5",
        "plop==0.3.0",
        "typing==3.6.1",
        # scipy only needed for scanpointgenerator.plot_generator
        "scipy==0.19.1",
        # DLS developed
        "annotypes==0.20",
        "cothread==2.14",
        "scanpointgenerator==2.2.1",
        "vdsgen==0.5.1"
    )
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "cothread"))
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "annotypes"))
    main()
