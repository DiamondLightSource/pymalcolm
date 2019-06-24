import os
import subprocess
from annotypes import Anno
from malcolm.core import StringMeta, Widget
from malcolm.modules.builtin.hooks import HaltHook
from malcolm.modules.builtin.controllers import BasicController, AMri
from malcolm import version
from malcolm.modules.ca.util import catools


def start_ioc(stats, prefix):
    db_macros = "prefix='%s'" % prefix
    for key, value in stats.items():
        db_macros += ",%s='%s'" % (key, value)
    root = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
    db_template = os.path.join(root, 'db', 'stats.template')
    ioc = subprocess.Popen(
        ["softIoc", "-m", db_macros, "-d", db_template],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    # wait for IOC to start
    pid_rbv = catools.caget("%s:PID" % prefix, timeout=5)
    if int(pid_rbv) != os.getpid():
        raise Exception("Got back different PID: " +
                        "is there another stats instance on the machine?")
    catools.caput("%s:YAML:PATH" % prefix, stats["yaml_path"],
                  datatype=catools.DBR_CHAR_STR)
    catools.caput("%s:PYMALCOLM:PATH" % prefix, stats["pymalcolm_path"],
                  datatype=catools.DBR_CHAR_STR)
    return ioc


def parse_yaml_version(file_path, work_area, prod_area):
    ver = "unknown"
    if file_path.startswith(work_area):
        ver = "Work"
    elif file_path.startswith(prod_area):
        cwd = os.getcwd()
        os.chdir(os.path.split(file_path)[0])
        try:
            ver = subprocess.check_output(
                ['/usr/bin/git', 'describe',
                 '--tags', '--exact-match']).strip(b'\n')
        except subprocess.CalledProcessError:
            ver = "Prod (unknown version)"
            print("Git error when parsing yaml version")

        os.chdir(cwd)
    return ver


with Anno("prefix for stats PVs"):
    APvPrefix = str


class StatsController(BasicController):
    def __init__(self, mri="devStats", prefix=""):
        # type: (AMri, APvPrefix) -> None
        super(StatsController, self).__init__(mri)

        stats = dict()
        cwd = os.getcwd()
        sys_call_bytes = open('/proc/%s/cmdline' % os.getpid(),
                              'rb').read().split(
            b'\0')
        sys_call = [el.decode("utf-8") for el in sys_call_bytes]
        if sys_call[1].startswith('/'):
            stats["pymalcolm_path"] = sys_call[1]
        else:
            stats["pymalcolm_path"] = os.path.join(cwd, sys_call[1])

        if sys_call[2].startswith('/'):
            stats["yaml_path"] = sys_call[2]
        else:
            stats["yaml_path"] = os.path.join(cwd, sys_call[2])

        stats["yaml_ver"] = parse_yaml_version(stats["yaml_path"],
                                               '/dls_sw/work', '/dls_sw/prod')

        stats["pymalcolm_ver"] = version.__version__
        hostname = os.uname()[1]
        stats["kernel"] = "%s %s" % (os.uname()[0], os.uname()[2])
        stats["hostname"] = hostname if len(hostname) < 39 else hostname[
                                                                :35] + '...'
        stats["pid"] = os.getpid()

        self.pymalcolm_path = StringMeta(
            "Path to pymalcolm executable",
            tags=[Widget.MULTILINETEXTUPDATE.tag()]).create_attribute_model(
            stats["pymalcolm_path"])
        self.field_registry.add_attribute_model("pymalcolmPath",
                                                self.pymalcolm_path)
        self.pymalcolm_ver = StringMeta(
            "Version of pymalcolm executable",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            stats["pymalcolm_ver"])
        self.field_registry.add_attribute_model("pymalcolmVer",
                                                self.pymalcolm_ver)
        self.yaml_path = StringMeta(
            "Path to yaml configuration file",
            tags=[Widget.MULTILINETEXTUPDATE.tag()]).create_attribute_model(
            stats["yaml_path"])
        self.field_registry.add_attribute_model("yamlPath", self.yaml_path)
        self.yaml_ver = StringMeta(
            "version of yaml configuration file",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            stats["yaml_ver"])
        self.field_registry.add_attribute_model("yamlVer", self.yaml_ver)
        self.hostname = StringMeta(
            "Name of host machine",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            stats["hostname"])
        self.field_registry.add_attribute_model("hostname", self.hostname)
        self.kernel = StringMeta(
            "Kernel of host machine",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            stats["kernel"])
        self.field_registry.add_attribute_model("kernel", self.kernel)
        self.pid = StringMeta(
            "process ID of pymalcolm instance",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            stats["pid"])
        self.field_registry.add_attribute_model("pid", self.pid)

        self.ioc = start_ioc(stats, prefix)

        self.register_hooked(HaltHook, self.ioc.terminate)
