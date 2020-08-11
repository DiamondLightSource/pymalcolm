import os
from collections import OrderedDict

from annotypes import Anno

from malcolm.core import (
    Part,
    PartRegistrar,
    StringArrayMeta,
    StringMeta,
    TableMeta,
    Widget,
    alarm,
)
from malcolm.modules import ca
from malcolm.modules.builtin import hooks, infos, parts

with Anno("name of IOC"):
    AIoc = str


class DirParsePart(Part):
    registrar = None
    ioc_prod_root = ""
    dls_version = None

    def __init__(self, name: parts.APartName, ioc: AIoc) -> None:
        super().__init__(name)

        self.dls_ver_pv = ca.util.CAAttribute(
            StringMeta("IOC version"),
            ca.util.catools.DBR_STRING,
            "",
            ioc + ":DLSVER",
            throw=False,
            callback=self.version_updated,
        )
        self.dir1_pv = ca.util.CAAttribute(
            StringMeta("IOC directory pt1"),
            ca.util.catools.DBR_STRING,
            "",
            ioc + ":APP_DIR1",
            widget=Widget.NONE,
            throw=False,
            callback=self.set_dir1,
        )
        self.dir2_pv = ca.util.CAAttribute(
            StringMeta("IOC directory pt2"),
            ca.util.catools.DBR_STRING,
            "",
            ioc + ":APP_DIR2",
            widget=Widget.NONE,
            throw=False,
            callback=self.set_dir2,
        )

        self.autosave_status_pv = ca.util.CAAttribute(
            StringMeta("IOC Status"),
            ca.util.catools.DBR_STRING,
            "",
            ioc + ":STATUS",
            throw=False,
            callback=self.set_procserv_state,
        )

        self.dir1 = None
        self.dir2 = None
        self.dir = ""

        self.has_procserv = False

        elements = OrderedDict()
        elements["module"] = StringArrayMeta("Module", tags=[Widget.TEXTUPDATE.tag()])
        elements["path"] = StringArrayMeta("Path", tags=[Widget.TEXTUPDATE.tag()])

        self.dependencies = TableMeta(
            "Modules which this IOC depends on",
            tags=[Widget.TABLE.tag()],
            writeable=False,
            elements=elements,
        ).create_attribute_model({"module": [], "path": []})

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.add_attribute_model("dlsVersion", self.dls_ver_pv.attr)
        registrar.add_attribute_model("dir1", self.dir1_pv.attr)
        registrar.add_attribute_model("dir2", self.dir2_pv.attr)
        registrar.add_attribute_model("autosaveStatus", self.autosave_status_pv.attr)
        registrar.add_attribute_model("dependencies", self.dependencies)

        self.register_hooked(hooks.DisableHook, self.disconnect)
        self.register_hooked((hooks.InitHook, hooks.ResetHook), self.reconnect)

    def reconnect(self):
        self.dls_ver_pv.reconnect()
        self.dir1_pv.reconnect()
        self.dir2_pv.reconnect()
        self.autosave_status_pv.reconnect()

    def disconnect(self):
        self.dls_ver_pv.disconnect()
        self.dir1_pv.disconnect()
        self.dir2_pv.disconnect()
        self.autosave_status_pv.disconnect()

    def set_procserv_state(self, value):
        if value.ok:
            self.has_procserv = True
            self.version_updated(self.dls_version)

    def version_updated(self, value):
        if value is not None and value.ok:
            self.dls_version = value
            if isinstance(value, str):
                if value.lower() == "work" or value.lower() == "other":
                    message = "IOC running from non-prod area"
                    stat = alarm.Alarm(
                        message=message, severity=alarm.AlarmSeverity.MINOR_ALARM
                    )
                    self.registrar.report(infos.HealthInfo(stat))
                else:
                    message = "OK"
                    stat = alarm.Alarm(
                        message=message, severity=alarm.AlarmSeverity.NO_ALARM
                    )
                    self.registrar.report(infos.HealthInfo(stat))

        else:
            if self.has_procserv:
                message = "IOC not running (procServ enabled)"
                stat = alarm.Alarm(
                    message=message, severity=alarm.AlarmSeverity.UNDEFINED_ALARM
                )
                self.registrar.report(infos.HealthInfo(stat))
            else:
                message = "neither IOC nor procServ are running"
                stat = alarm.Alarm(
                    message=message, severity=alarm.AlarmSeverity.INVALID_ALARM
                )
                self.registrar.report(infos.HealthInfo(stat))

    def set_dir1(self, value):
        if value.ok:
            self.dir1 = value
        if self.dir1 is not None and self.dir2 is not None:
            self.dir = self.dir1 + self.dir2
            self.parse_release()

    def set_dir2(self, value):
        if value.ok:
            self.dir2 = value
        if self.dir1 is not None and self.dir2 is not None:
            self.dir = self.dir1 + self.dir2
            self.parse_release()

    def parse_release(self):
        release_file = os.path.join(self.dir, "configure", "RELEASE")
        dependencies = OrderedDict()
        dependency_table = OrderedDict()
        if os.path.isdir(self.dir) and os.path.isfile(release_file):
            with open(release_file, "r") as release:
                dep_list = release.readlines()
                dep_list = [
                    dep.strip("\n") for dep in dep_list if not dep.startswith("#")
                ]
                for dep in dep_list:
                    dep_split = dep.replace(" ", "").split("=")
                    if len(dep_split) == 2:
                        dependencies[dep_split[0]] = dep_split[1]
                dependency_table["module"] = []
                dependency_table["path"] = []
                for k1, v1 in dependencies.items():
                    for k2, v2 in dependencies.items():
                        dependencies[k2] = v2.replace("$(%s)" % k1, v1)

                for k1, v1 in dependencies.items():
                    dependency_table["module"] += [k1]
                    dependency_table["path"] += [v1]

            if len(dep_list) > 0:
                self.dependencies.set_value(dependency_table)

        else:
            status = alarm.Alarm(
                message="reported IOC directory not found",
                severity=alarm.AlarmSeverity.MINOR_ALARM,
            )
            self.dependencies.set_alarm(status)
