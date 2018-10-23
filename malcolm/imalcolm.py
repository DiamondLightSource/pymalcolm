#!/dls_sw/prod/tools/RHEL6-x86_64/defaults/bin/dls-python
import logging.config
import threading
import argparse
import atexit
import getpass
import json
import collections
import os
import signal
import sys
import time

from enum import Enum


class ProfilerMode(Enum):
    # Profile modes for use in the interrupt func
    PROF = (signal.ITIMER_PROF, signal.SIGPROF)
    VIRTUAL = (signal.ITIMER_VIRTUAL, signal.SIGVTALRM)
    REAL = (signal.ITIMER_REAL, signal.SIGALRM)


# A combination of plop.Collector and plot.Formatter
class Profiler(object):
    def __init__(self, dirname, mode=ProfilerMode.PROF, interval=0.0001):
        # type: (str, ProfilerMode, float) -> None
        self.dirname = dirname
        self.mode = mode
        self.interval = interval
        self.start_time = None
        self.running = False
        self.stopping = False
        self.stacks = []
        sig = mode.value[1]
        signal.signal(sig, self.handler)
        signal.siginterrupt(sig, False)

    def handler(self, sig, current_frame):
        from malcolm.compat import get_thread_ident

        if self.stopping:
            # Told to stop, cancel timer and return
            timer = self.mode.value[0]
            signal.setitimer(timer, 0, 0)
            self.running = False
        else:
            current_tid = get_thread_ident()
            for tid, frame in sys._current_frames().items():
                if tid == current_tid:
                    frame = current_frame
                frames = []
                while frame is not None:
                    code = frame.f_code
                    frames.append(
                        (code.co_filename, code.co_firstlineno, code.co_name))
                    frame = frame.f_back
                self.stacks.append(frames)

    def start(self):
        assert not self.running, "Profiler already started"
        self.start_time = time.time()
        self.running = True
        self.stacks = []
        timer = self.mode.value[0]
        signal.setitimer(timer, self.interval, self.interval)

    def stop(self, filename=None):
        assert self.running, "Profiler already stopped"
        self.stopping = True
        while self.running:
            pass  # need busy wait; ITIMER_PROF doesn't proceed while sleeping
        # If not given a filename, calculate one
        if not filename:
            start_date = time.strftime(
                '%Y%m%d-%H%M%S', time.localtime(self.start_time))
            duration = time.time() - self.start_time
            filename = "%s-for-%ds.plop" % (start_date, duration)
        # Format to be compatible with plop viewer
        stack_counts = collections.Counter(
            tuple(frames) for frames in self.stacks)
        max_stacks = 50
        stack_counts = dict(sorted(stack_counts.items(),
                                   key=lambda kv: -kv[1])[:max_stacks])
        with open(os.path.join(self.dirname, filename), "w") as f:
            f.write(repr(stack_counts))
        return filename


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
    logging.config.dictConfig(log_config)

    # Now make a queue listener that consumes messages on the queue and forwards
    # them to any of the appropriate original root handlers
    handlers = [logging._handlers[h] for h in root_handlers]
    listener = QueueListener(q, *handlers, respect_handler_level=True)
    return listener


def parse_args():
    parser = argparse.ArgumentParser(
        description="Interactive shell for malcolm")
    parser.add_argument(
        '--client', '-c',
        help="Add a client to given server, like ws://localhost:8080 or pva")
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
    from malcolm.compat import queue, get_profiler_dir

    args = parse_args()

    # Make some log config, either fron command line or
    log_config = make_logging_config(args)

    # Start it off, and tell it to stop when we quit
    listener = make_async_logging(log_config)
    listener.start()
    atexit.register(listener.stop)

    # Setup profiler dir
    profiledir = get_profiler_dir()
    if not os.path.isdir(profiledir):
        os.mkdir(profiledir)
    profiler = Profiler(profiledir)
    profiler.start()

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
    from malcolm.core import Context, Queue
    from malcolm.modules.builtin.blocks import proxy_block

    # Make a user context
    class UserContext(Context):
        def make_queue(self):
            return Queue(user_facing=True)

        def post(self, path, params=None, timeout=None, event_timeout=None):
            try:
                return super(UserContext, self).post(
                    path, params, timeout, event_timeout)
            except KeyboardInterrupt:
                self.post([path[0], "abort"])
                raise

        def make_proxy(self, comms, mri):
            # Need to do this in cothread's thread
            cothread.CallbackResult(
                process.add_controller, proxy_block(comms=comms, mri=mri)[-1])

    self = UserContext(process)
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
""" % (self.mri_list,)

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
    print("Loading...")

    os.environ["EPICS_CA_MAX_ARRAY_BYTES"] = "6000000"

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

    require("tornado", "numpy", "ruamel.yaml", "cothread==2.14", "vdsgen>=0.3",
            "pygelf==0.3.1", "scanpointgenerator==2.1.1", "plop", "h5py>=2.8",
            "annotypes>=0.9")
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "cothread"))
    #sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "annotypes"))
    sys.path.append(
        "/dls_sw/work/R3.14.12.3/support/pvaPy/lib/python/2.7/linux-x86_64")

    main()
