from malcolm.core import StringMeta, Widget, Alarm, AlarmSeverity, Part
from malcolm.modules.builtin import hooks, infos, parts
from malcolm import version
from malcolm.modules.ca.util import catools

import os
import subprocess
from annotypes import Anno

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
                 '--tags', '--exact-match']).strip(b'\n').decode("utf-8")
        except subprocess.CalledProcessError:
            ver = "Prod (unknown version)"
            print("Git error when parsing yaml version")

        os.chdir(cwd)
    return ver


with Anno("prefix for self.stats PVs"):
    APvPrefix = str


class StatsPart(Part):
    def __init__(self, name, prefix):
        # type: (parts.APartName, APvPrefix,) -> None
        super(StatsPart, self).__init__(name)
        self.ioc = None
        self.prefix = prefix
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
        self.stats["hostname"] = hostname if len(hostname) < 39 else hostname[
                                                                     :35] + '...'
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

    def start_ioc(self):
        if self.ioc is None:
            self.ioc = start_ioc(self.stats, self.prefix)

    def stop_ioc(self):
        if self.ioc is not None:
            self.ioc.terminate()
            self.ioc = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(StatsPart, self).setup(registrar)
        registrar.add_attribute_model("pymalcolmPath", self.pymalcolm_path)
        registrar.add_attribute_model("pymalcolmVer", self.pymalcolm_ver)
        registrar.add_attribute_model("yamlPath", self.yaml_path)
        registrar.add_attribute_model("yamlVer", self.yaml_ver)
        registrar.add_attribute_model("hostname", self.hostname)
        registrar.add_attribute_model("kernel", self.kernel)
        registrar.add_attribute_model("pid", self.pid)

        if self.stats["yaml_ver"] in ["Work", "unknown"]:
            message = "Non-prod YAML config"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
            registrar.report(infos.HealthInfo(alarm))

        registrar.hook(hooks.InitHook, self.start_ioc)

        registrar.hook(hooks.HaltHook, self.stop_ioc)
