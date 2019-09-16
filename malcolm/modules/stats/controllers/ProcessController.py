from malcolm.modules import builtin

from malcolm.core import StringMeta, Widget, Alarm, AlarmSeverity, \
    ProcessStartHook, ProcessStopHook, Subscribe
from malcolm.modules.builtin.util import LayoutTable
from malcolm import version
from malcolm.modules.ca.util import catools
from malcolm.modules.ca.parts import CAActionPart, CAStringPart
from malcolm.modules.stats.parts import IocStatusPart

import os
import subprocess
import re
from annotypes import Anno, add_call_types
import cothread


def await_ioc_start(stats, prefix):
    cothread.Yield()
    pid_rbv = catools.caget("%s:PID" % prefix, timeout=5)
    if int(pid_rbv) != os.getpid():
        raise Exception("Got back different PID: " +
                        "is there another stats instance on the machine?")
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
        epics_base = "/dls_sw/epics/R3.14.12.7/base"
    softIoc_bin = epics_base + "/bin/linux-x86_64/softIoc"
    for key, value in stats.items():
        db_macros += ",%s='%s'" % (key, value)
    root = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
    db_template = os.path.join(root, 'db', 'stats.template')
    ioc = subprocess.Popen(
        [softIoc_bin, "-m", db_macros, "-d", db_template],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    cothread.Spawn(await_ioc_start, stats, prefix)
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
                 '--tags', '--exact-match']).strip(b'\n').decode("utf-8")
        except subprocess.CalledProcessError:
            ver = "Prod (unknown version)"
            print("Git error when parsing yaml version")

        os.chdir(cwd)
    return ver


with Anno("prefix for self.stats PVs"):
    APvPrefix = str
with Anno("parse beamline IOCs from redirect table"):
    AParseIOCs = bool
with Anno("prefix to search for when parsing redirect table"):
    ABLPrefix = str


def parse_redirect_table(file_path, bl_prefix):
    with open(file_path, 'r') as redirector:
        table = redirector.read()
        bl_iocs = re.findall(bl_prefix + "-[A-Z][A-Z]-IOC-[0-9][0-9] ",
                             table)
    return bl_iocs


class ProcessController(builtin.controllers.ManagerController):
    def __init__(self,
                 mri,  # type: builtin.controllers.AMri
                 prefix,  # type: APvPrefix
                 config_dir,  # type: builtin.controllers.AConfigDir
                 parse_iocs=False,  # type: AParseIOCs
                 bl_prefix="",  # type: ABLPrefix
                 ):
        # type: (...) -> None
        super(ProcessController, self).__init__(mri, config_dir)
        self.ioc = None
        self.bl_iocs = []
        self.ioc_blocks = dict()
        self.prefix = prefix
        self.parse_iocs = parse_iocs
        self.bl_prefix = bl_prefix
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

        self.stats["yaml_ver"] = parse_yaml_version(self.stats["yaml_path"],
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
        if self.parse_iocs:
            assert self.bl_prefix != "", \
                'parse_iocs set to True but no bl_prefix given'
            self.get_ioc_list('/dls_sw/prod/etc/redirector/redirect_table',
                              self.bl_prefix)
        super(ProcessController, self).init()

    def set_default_layout(self):
        name = []
        mri = []
        x = []
        y = []
        visible = []
        for part_name in self.parts.keys():
            if isinstance(self.parts[part_name], builtin.parts.ChildPart):
                part_mri = self.parts[part_name].mri
                if part_mri in self.ioc_blocks.keys():
                    visible += [self.ioc_blocks[part_mri]
                                    .controller.health.alarm.severity !=
                                AlarmSeverity.INVALID_ALARM]

                else:
                    visible += [True]
                x += [0]
                y += [0]
                name += [part_name]
                mri += [part_mri]

        self.set_layout(LayoutTable(name, mri, x, y, visible))

    def stop_ioc(self):
        if self.ioc is not None:
            self.ioc.terminate()
            self.ioc = None

    def get_ioc_list(self, file_path, bl_prefix):
        self.bl_iocs = parse_redirect_table(file_path, bl_prefix)
        for ioc in self.bl_iocs:
            ioc = ioc[:-1]
            self.ioc_blocks[ioc + ':STATUS'] = IocStatusBlock(ioc)
            self.process.add_controller(
                self.ioc_blocks[ioc + ':STATUS'].controller)
            self.add_part(
                builtin.parts.ChildPart(name=ioc, mri=ioc + ":STATUS"))

    # Following code is not needed:
    # Have the web & PVA server blocks included as part of the stats block

    # def check_all_blocks(self):
    #     num_pandas = 0
    #     for mri in self.process.mri_list:
    #         controller = self.process.get_controller(mri)
    #         if isinstance(controller, HTTPServerComms):
    #             self.add_part(
    #                 builtin.parts.ChildPart(name="WEB", mri=controller.mri))
    #         if isinstance(controller, PvaServerComms):
    #             self.add_part(
    #                 builtin.parts.ChildPart(name="PVA", mri=controller.mri))
    #         if isinstance(controller, PandAManagerController):
    #             num_pandas += 1
    #             self.add_part(
    #                 builtin.parts.ChildPart(name="PandA-%02d" % num_pandas,
    #                                         mri=controller.mri))
    #     self.set_layout(builtin.util.LayoutTable([], [], [], [], []))


class IocStatusBlock(object):
    def __init__(self, ioc):
        self.ioc = ioc
        self.mri = (ioc + ":STATUS")
        self.controller = builtin.controllers.StatefulController(self.mri)
        self.dirParsePart = IocStatusPart(name=ioc)
        self.dirParsePart.register_hooked(builtin.hooks.InitHook,
                                          self.init_handler)
        self.controller.add_part(self.dirParsePart)

        self.host_arch = CAStringPart(
            name="hostArch",
            description="Host Architecture",
            rbv=(ioc + ":KERNEL_VERS"),
            throw=False)

        self.controller.add_part(self.host_arch)

        self.controller.add_part(CAStringPart(
            name="currentVersion",
            description="IOC version",
            rbv=(ioc + ":DLSVER"),
            throw=False))

        self.controller.add_part(CAStringPart(
            name="iocDirectory1",
            description="IOC directory",
            rbv=(ioc + ":APP_DIR1"),
            throw=False,
            widget=Widget.NONE))

        self.controller.add_part(CAStringPart(
            name="iocDirectory2",
            description="IOC directory",
            rbv=(ioc + ":APP_DIR2"),
            throw=False,
            widget=Widget.NONE))

        self.controller.add_part(CAStringPart(
            name="epicsVersion",
            description="EPICS version",
            rbv=(ioc + ":EPICS_VERS"),
            throw=False))

    @add_call_types
    def init_handler(self):
        # type: () -> None
        cothread.Spawn(self.check_pvs_and_subscribe)

    def check_pvs_and_subscribe(self):
        cothread.Yield()
        pv_test = catools.caget(
            [self.ioc + ":SRSTATUS", self.ioc + ":RESTART"],
            throw=False)

        if pv_test[0].ok:
            part = CAStringPart("autosaveStatus",
                                description="status of Autosave",
                                rbv=(self.ioc + ":SRSTATUS"))
            self.dirParsePart.autosave_pv = part
            self.controller.add_part(self.dirParsePart.autosave_pv,
                                     add_fields=True)

        if pv_test[1].ok:
            part = CAActionPart("restartIoc",
                                description="restart IOC via procServ",
                                pv=(self.ioc + ":RESTART"))
            self.dirParsePart.restart_pv = part
            self.controller.add_part(self.dirParsePart.restart_pv,
                                     add_fields=True)
        arch = self.host_arch.caa.attr.value
        if arch.startswith("WIND"):
            self.controller.add_part(builtin.parts.IconPart(
                svg=(os.path.split(__file__)[0] + "/../icons/vx_epics.svg")),
                add_fields=True)
        elif arch.startswith("Linux"):
            self.controller.add_part(builtin.parts.IconPart(
                svg=(os.path.split(__file__)[0] + "/../icons/linux_epics.svg")),
                add_fields=True)
        elif arch.startswith("Windows"):
            self.controller.add_part(builtin.parts.IconPart(
                svg=(os.path.split(__file__)[0] + "/../icons/win_epics.svg")),
                add_fields=True)
        else:
            self.controller.add_part(builtin.parts.IconPart(
                svg=(os.path.split(__file__)[0] + "/../icons/epics-logo.svg")),
                add_fields=True)

        subscribe_ver = Subscribe(path=[self.mri, "currentVersion"])
        subscribe_ver.set_callback(self.dirParsePart.version_updated)
        self.controller.handle_request(subscribe_ver).wait()
        subscribe_dir1 = Subscribe(path=[self.mri, "iocDirectory1"])
        subscribe_dir1.set_callback(self.dirParsePart.set_dir1)
        self.controller.handle_request(subscribe_dir1).wait()
        subscribe_dir2 = Subscribe(path=[self.mri, "iocDirectory2"])
        subscribe_dir2.set_callback(self.dirParsePart.set_dir2)
        self.controller.handle_request(subscribe_dir2).wait()
