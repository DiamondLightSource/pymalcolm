import os
from collections import OrderedDict

from annotypes import Anno

from malcolm.modules.builtin import parts, infos
from malcolm.core import TableMeta, \
    StringArrayMeta, Widget, PartRegistrar, Part
from malcolm.core.alarm import AlarmSeverity, Alarm

with Anno("is procserv running for this IOC?"):
    AHasProcserv = bool

class DirParsePart(Part):
    registrar = None
    ioc_prod_root = ''
    dls_version = None
    # dbl = []

    def __init__(self, name, has_procserv):
        # type: (parts.APartName, AHasProcserv) -> None
        super(DirParsePart, self).__init__(name)
        # Hooks
        self.dir1 = None
        self.dir2 = None
        self.dir = ""
        self.has_procserv = has_procserv

        elements = OrderedDict()
        elements["module"] = StringArrayMeta("Module",
                                             tags=[Widget.TEXTUPDATE.tag()])
        elements["path"] = StringArrayMeta("Path",
                                           tags=[Widget.TEXTUPDATE.tag()])

        self.dependencies = TableMeta("Modules which this IOC depends on",
                                      tags=[Widget.TABLE.tag()],
                                      writeable=False,
                                      elements=elements)\
            .create_attribute_model({"module": [], "path": []})

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(DirParsePart, self).setup(registrar)
        registrar.add_attribute_model("dependencies", self.dependencies)

    def version_updated(self, update):
        self.dls_version = update.value["value"]
        if isinstance(update.value["value"], str) and update.value[
            "value"].lower() == "work":
            message = "IOC running from work area"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
            self.registrar.report(infos.HealthInfo(alarm))
        elif update.value["alarm"].severity == AlarmSeverity.UNDEFINED_ALARM:
            if self.has_procserv:
                message = "IOC not running (procServ enabled)"
                alarm = Alarm(message=message,
                              severity=AlarmSeverity.UNDEFINED_ALARM)
                self.registrar.report(infos.HealthInfo(alarm))                
            else:
                message = "neither IOC nor procServ are running"
                alarm = Alarm(message=message,
                              severity=AlarmSeverity.INVALID_ALARM)
                self.registrar.report(infos.HealthInfo(alarm))

    def set_dir1(self, update):
        self.dir1 = update.value["value"]
        if self.dir1 is not None and self.dir2 is not None:
            self.dir = self.dir1 + self.dir2
            self.parse_release()

    def set_dir2(self, update):
        self.dir2 = update.value["value"]
        if self.dir1 is not None and self.dir2 is not None:
            self.dir = self.dir1 + self.dir2
            self.parse_release()

    def parse_release(self):
        release_file = os.path.join(self.dir, 'configure', 'RELEASE')
        dependencies = OrderedDict()
        dependency_table = OrderedDict()
        if os.path.isdir(self.dir) and os.path.isfile(release_file):
            with open(release_file, 'r') as release:
                dep_list = release.readlines()
                dep_list = [dep.strip('\n') for dep in dep_list if
                            not dep.startswith('#')]
                for dep in dep_list:
                    dep_split = dep.replace(' ', '').split('=')
                    if len(dep_split) == 2:
                        dependencies[dep_split[0]] = dep_split[1]
                dependency_table["module"] = []
                dependency_table["path"] = []
                for k1, v1 in dependencies.items():
                    for k2, v2 in dependencies.items():
                        dependencies[k2] = v2.replace('$(%s)' % k1, v1)

                for k1, v1 in dependencies.items():
                    dependency_table["module"] += [k1]
                    dependency_table["path"] += [v1]

            if len(dep_list) > 0:
                self.dependencies.set_value(dependency_table)

        else:
            self.dependencies.set_alarm(
                Alarm(message="reported IOC directory not found",
                      severity=AlarmSeverity.MINOR_ALARM)
            )
