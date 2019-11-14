import os
import subprocess
import re

import cothread
from annotypes import Anno
from collections import OrderedDict

from malcolm.modules import builtin
from malcolm.modules.ca.parts import CAStringPart, CAActionPart
from malcolm.core import StringMeta, Widget, Alarm, AlarmSeverity, \
    ProcessStartHook, ProcessStopHook
from malcolm.modules.builtin.util import LayoutTable
from malcolm import version
from malcolm.modules.ca.util import catools
from ..parts.iociconpart import IocIconPart
from ..parts.dirparsepart import DirParsePart


def await_ioc_start(stats, prefix):
    cothread.Yield()
    pid_rbv = catools.caget("%s:PID" % prefix, timeout=5)
    if int(pid_rbv) != os.getpid():
        raise Exception("Got back different PID: " +
                        "is there another system instance on the machine?")
    catools.caput("%s:YAML:PATH" % prefix, stats["yaml_path"],
                  datatype=catools.DBR_CHAR_STR)
    catools.caput("%s:PYMALCOLM:PATH" % prefix, stats["pymalcolm_path"],
                  datatype=catools.DBR_CHAR_STR)


def start_ioc(stats, prefix):
    db_macros = "prefix='%s'" % prefix
    epics_base = None
    try:
        epics_base = os.environ["EPICS_BASE"]
    except KeyError:
        raise Exception("EPICS base not defined in environment")
    softIoc_bin = epics_base + "/bin/linux-x86_64/softIoc"
    for key, value in stats.items():
        db_macros += ",%s='%s'" % (key, value)
    root = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
    db_template = os.path.join(root, 'db', 'system.template')
    ioc = subprocess.Popen(
        [softIoc_bin, "-m", db_macros, "-d", db_template],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    cothread.Spawn(await_ioc_start, stats, prefix)
    return ioc


with Anno("prefix for self.system PVs"):
    APvPrefix = str
with Anno("parse beamline IOCs from redirect table"):
    AParseIOCs = bool
with Anno("prefix to search for when parsing redirect table"):
    ABLPrefix = str
with Anno("path to IOC redirect table"):
    AIocLookupPath = str


def parse_redirect_table(file_path, bl_prefix):
    with open(file_path, 'r') as redirector:
        table = redirector.read()
        bl_iocs = re.findall(bl_prefix + "-[A-Z][A-Z]-IOC-[0-9][0-9] ",
                             table)
    for ind, ioc in enumerate(bl_iocs):
        bl_iocs[ind] = ioc.strip()
    return bl_iocs


class ProcessController(builtin.controllers.ManagerController):
    def __init__(self,
                 mri,  # type: builtin.controllers.AMri
                 prefix,  # type: APvPrefix
                 config_dir,  # type: builtin.controllers.AConfigDir
                 ioc_lookup_path="",  # type: AIocLookupPath
                 bl_prefix="",  # type: ABLPrefix
                 ):
        # type: (...) -> None
        super(ProcessController, self).__init__(mri, config_dir)
        self.ioc = None
        self.bl_iocs = []
        self.ioc_blocks = OrderedDict()
        self.prefix = prefix
        self.bl_prefix = bl_prefix
        self.ioc_lookup_path = ioc_lookup_path
        self.stats = dict()
        cwd = os.getcwd()
        sys_call_bytes = open('/proc/%s/cmdline' % os.getpid(),
                              'rb').read().split(
            b'\0')
        sys_call = [el.decode("utf-8") for el in sys_call_bytes]
        if sys_call[1].startswith('/'):
            self.stats["pymalcolm_path"] = sys_call[1]
        else:
            self.stats["pymalcolm_path"] = os.path.join(cwd, sys_call[1])

        if sys_call[2].startswith('/'):
            self.stats["yaml_path"] = sys_call[2]
        else:
            self.stats["yaml_path"] = os.path.join(cwd, sys_call[2])

        self.stats["yaml_ver"] = self.parse_yaml_version(
            self.stats["yaml_path"],
            '/dls_sw/work',
            '/dls_sw/prod')

        if self.stats["pymalcolm_path"].startswith('/dls_sw/prod'):
            self.stats["pymalcolm_ver"] = version.__version__
        else:
            self.stats["pymalcolm_ver"] = "Work"
        hostname = os.uname()[1]
        self.stats["kernel"] = "%s %s" % (os.uname()[0], os.uname()[2])
        self.stats["hostname"] = \
            hostname if len(hostname) < 39 else hostname[:35] + '...'
        self.stats["pid"] = os.getpid()

        self.pymalcolm_path = StringMeta(
            "Path to pymalcolm executable",
            tags=[Widget.MULTILINETEXTUPDATE.tag()]).create_attribute_model(
            self.stats["pymalcolm_path"])
        self.pymalcolm_ver = StringMeta(
            "Version of pymalcolm executable",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["pymalcolm_ver"])
        self.yaml_path = StringMeta(
            "Path to yaml configuration file",
            tags=[Widget.MULTILINETEXTUPDATE.tag()]).create_attribute_model(
            self.stats["yaml_path"])
        self.yaml_ver = StringMeta(
            "version of yaml configuration file",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["yaml_ver"])
        self.hostname = StringMeta(
            "Name of host machine",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["hostname"])
        self.kernel = StringMeta(
            "Kernel of host machine",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["kernel"])
        self.pid = StringMeta(
            "process ID of pymalcolm instance",
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(
            self.stats["pid"])

        self.field_registry.add_attribute_model("pymalcolmPath",
                                                self.pymalcolm_path)
        self.field_registry.add_attribute_model("pymalcolmVer",
                                                self.pymalcolm_ver)
        self.field_registry.add_attribute_model("yamlPath", self.yaml_path)
        self.field_registry.add_attribute_model("yamlVer", self.yaml_ver)
        self.field_registry.add_attribute_model("hostname", self.hostname)
        self.field_registry.add_attribute_model("kernel", self.kernel)
        self.field_registry.add_attribute_model("pid", self.pid)

        if self.stats["yaml_ver"] in ["Work", "unknown"]:
            message = "Non-prod YAML config"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
            self.update_health("", builtin.infos.HealthInfo(alarm))

        self.register_hooked(ProcessStartHook, self.init)

        self.register_hooked(ProcessStopHook, self.stop_ioc)

    def init(self):
        if self.ioc is None:
            self.ioc = start_ioc(self.stats, self.prefix)
        if self.bl_prefix and self.ioc_lookup_path:
            self.get_ioc_list(self.ioc_lookup_path, self.bl_prefix)
        super(ProcessController, self).init()

    def set_default_layout(self):
        name = []
        mri = []
        x = []
        y = []
        visible = []
        for part_name in self.parts.keys():
            if isinstance(self.parts[part_name], builtin.parts.ChildPart):
                visible += [True]
                x += [0]
                y += [0]
                name += [part_name]
                mri += [self.parts[part_name].mri]

        self.set_layout(LayoutTable(name, mri, x, y, visible))

    def stop_ioc(self):
        if self.ioc is not None:
            self.ioc.terminate()
            self.ioc = None

    def get_ioc_list(self, file_path, bl_prefix):
        self.bl_iocs = parse_redirect_table(file_path, bl_prefix)
        ioc_controllers = []
        for ioc in self.bl_iocs:
            ioc_controller = make_ioc_status(ioc)
            ioc_controllers += [ioc_controller]
        self.process.add_controllers(ioc_controllers)
        for ioc in self.bl_iocs:
            self.add_part(
                builtin.parts.ChildPart(name=ioc, mri=ioc + ":STATUS"))

    def parse_yaml_version(self, file_path, work_area, prod_area):
        ver = "unknown"
        if file_path.startswith(work_area):
            ver = "Work"
        elif file_path.startswith(prod_area):
            ver = self._run_git_cmd('describe', '--tags', '--exact-match',
                                    dir=os.path.split(file_path)[0])
            if ver is None:
                return "Prod (unknown version)"
            ver = ver.strip(b'\n').decode("utf-8")
        return ver


def make_ioc_status(ioc):
    controller = builtin.controllers.StatefulController(ioc + ":STATUS")

    controller.add_part(CAStringPart(
        name="epicsVersion",
        description="EPICS version",
        rbv=(ioc + ":EPICS_VERS"),
        throw=False))

    controller.add_part(IocIconPart(ioc, (os.path.split(__file__)[0] +
                                          "/../icons/epics-logo.svg")))
    controller.add_part(DirParsePart(ioc, ioc))

    controller.add_part(CAActionPart("restartIoc",
                                     description="restart IOC via procServ",
                                     pv=(ioc + ":RESTART"), throw=False))

    return controller



