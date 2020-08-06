import os
import subprocess
from collections import OrderedDict

import cothread
from annotypes import Anno

from malcolm import __version__
from malcolm.core import (
    Alarm,
    AlarmSeverity,
    BadValueError,
    ProcessStartHook,
    ProcessStopHook,
    StringMeta,
    Widget,
)
from malcolm.modules import builtin, ca
from malcolm.modules.ca.util import catools

from ..parts.dirparsepart import DirParsePart
from ..parts.iociconpart import IocIconPart


def await_ioc_start(stats, prefix):
    cothread.Yield()
    pid_rbv = catools.caget("%s:PID" % prefix, timeout=5)
    if int(pid_rbv) != os.getpid():
        raise BadValueError(
            "Got back different PID: "
            + "is there another system instance on the machine?"
        )
    catools.caput(
        "%s:YAML:PATH" % prefix, stats["yaml_path"], datatype=catools.DBR_CHAR_STR
    )
    catools.caput(
        "%s:PYMALCOLM:PATH" % prefix,
        stats["pymalcolm_path"],
        datatype=catools.DBR_CHAR_STR,
    )


def start_ioc(stats, prefix):
    db_macros = "prefix='%s'" % prefix
    try:
        epics_base = os.environ["EPICS_BASE"]
    except KeyError:
        raise BadValueError("EPICS base not defined in environment")
    softIoc_bin = epics_base + "/bin/linux-x86_64/softIoc"
    for key, value in stats.items():
        db_macros += ",%s='%s'" % (key, value)
    root = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
    db_template = os.path.join(root, "db", "system.template")
    ioc = subprocess.Popen(
        [softIoc_bin, "-m", db_macros, "-d", db_template],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    cothread.Spawn(await_ioc_start, stats, prefix)
    return ioc


with Anno("prefix for self.system PVs"):
    APvPrefix = str
with Anno("space-separated list of IOCs to monitor"):
    AIocList = str


class ProcessController(builtin.controllers.ManagerController):
    def __init__(
        self,
        mri: builtin.controllers.AMri,
        prefix: APvPrefix,
        config_dir: builtin.controllers.AConfigDir,
        ioc_list: AIocList = "",
    ) -> None:
        super().__init__(mri, config_dir)
        self.ioc = None
        self.ioc_blocks: OrderedDict = OrderedDict()
        self.prefix = prefix
        self.bl_iocs = ioc_list.split(" ")
        if self.bl_iocs[-1] == "":
            self.bl_iocs = self.bl_iocs[:-1]
        self.stats = dict()
        # TODO: the following stuff is all Linux-specific....
        sys_call_bytes = (
            open("/proc/%s/cmdline" % os.getpid(), "rb").read().split(b"\0")
        )
        sys_call = [el.decode("utf-8") for el in sys_call_bytes]
        self.stats["pymalcolm_path"] = os.path.abspath(sys_call[1])
        self.stats["yaml_path"] = os.path.abspath(sys_call[2])

        self.stats["yaml_ver"] = self.parse_yaml_version(
            self.stats["yaml_path"], "/dls_sw/work", "/dls_sw/prod"
        )

        self.stats["pymalcolm_ver"] = __version__
        hostname = os.uname()[1]
        self.stats["kernel"] = "%s %s" % (os.uname()[0], os.uname()[2])
        self.stats["hostname"] = (
            hostname if len(hostname) < 39 else hostname[:35] + "..."
        )
        self.stats["pid"] = str(os.getpid())

        self.pymalcolm_path = StringMeta(
            "Path to pymalcolm executable", tags=[Widget.MULTILINETEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["pymalcolm_path"])
        self.pymalcolm_ver = StringMeta(
            "Version of pymalcolm executable", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["pymalcolm_ver"])
        self.yaml_path = StringMeta(
            "Path to yaml configuration file", tags=[Widget.MULTILINETEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["yaml_path"])
        self.yaml_ver = StringMeta(
            "version of yaml configuration file", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["yaml_ver"])
        self.hostname = StringMeta(
            "Name of host machine", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["hostname"])
        self.kernel = StringMeta(
            "Kernel of host machine", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["kernel"])
        self.pid = StringMeta(
            "process ID of pymalcolm instance", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model(self.stats["pid"])

        self.field_registry.add_attribute_model("pymalcolmPath", self.pymalcolm_path)
        self.field_registry.add_attribute_model("pymalcolmVer", self.pymalcolm_ver)
        self.field_registry.add_attribute_model("yamlPath", self.yaml_path)
        self.field_registry.add_attribute_model("yamlVer", self.yaml_ver)
        self.field_registry.add_attribute_model("hostname", self.hostname)
        self.field_registry.add_attribute_model("kernel", self.kernel)
        self.field_registry.add_attribute_model("pid", self.pid)

        if self.stats["yaml_ver"] in ["work", "unknown"]:
            message = "Non-prod YAML config"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
            self.update_health("", builtin.infos.HealthInfo(alarm))

        self.register_hooked(ProcessStartHook, self.init)

        self.register_hooked(ProcessStopHook, self.stop_ioc)

    def init(self):
        if self.ioc is None:
            self.ioc = start_ioc(self.stats, self.prefix)
        self.get_ioc_list()
        super().init()
        msg = (
            """\
pymalcolm %(pymalcolm_ver)s started

Path: %(pymalcolm_path)s
Yaml: %(yaml_path)s"""
            % self.stats
        )
        self._run_git_cmd("commit", "--allow-empty", "-m", msg)

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

        self.set_layout(builtin.util.LayoutTable(name, mri, x, y, visible))

    def stop_ioc(self):
        if self.ioc is not None:
            self.ioc.terminate()
            self.ioc = None

    def get_ioc_list(self):
        ioc_controllers = []
        for ioc in self.bl_iocs:
            ioc_controller = make_ioc_status(ioc)
            ioc_controllers += [ioc_controller]
        self.process.add_controllers(ioc_controllers)
        for ioc in self.bl_iocs:
            self.add_part(builtin.parts.ChildPart(name=ioc, mri=ioc + ":STATUS"))

    def parse_yaml_version(self, file_path, work_area, prod_area):
        ver = "unknown"
        if file_path.startswith(work_area):
            ver = "work"
        elif file_path.startswith(prod_area):
            ver = self._run_git_cmd(
                "describe", "--tags", "--exact-match", cwd=os.path.split(file_path)[0]
            )
            if ver is None:
                return "Prod (unknown version)"
            ver = ver.strip(b"\n").decode("utf-8")
        return ver


def make_ioc_status(ioc):
    controller = builtin.controllers.StatefulController(ioc + ":STATUS")

    controller.add_part(
        ca.parts.CAStringPart(
            name="epicsVersion",
            description="EPICS version",
            rbv=(ioc + ":EPICS_VERS"),
            throw=False,
        )
    )

    controller.add_part(
        IocIconPart(ioc, (os.path.split(__file__)[0] + "/../icons/epics-logo.svg"))
    )
    controller.add_part(DirParsePart(ioc, ioc))

    controller.add_part(
        ca.parts.CAActionPart(
            "restartIoc",
            description="restart IOC via procServ",
            pv=(ioc + ":RESTART"),
            throw=False,
        )
    )

    return controller
