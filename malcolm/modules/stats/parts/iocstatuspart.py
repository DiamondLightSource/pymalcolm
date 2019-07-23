from malcolm.modules.builtin import parts, hooks, infos
from malcolm.core import Subscribe, TableMeta, \
    StringArrayMeta, Widget, PartRegistrar, Part
from malcolm.core.alarm import AlarmSeverity, Alarm
from malcolm.modules.ca.parts import CAStringPart

import os
from collections import OrderedDict

from annotypes import add_call_types, Anno

with Anno("does the IOC have autosave?"):
    AHasAutosave = bool


class IocStatusPart(Part):
    registrar = None
    ioc_prod_root = ''
    dls_version = None

    def __init__(self, name, mri, has_autosave=True):
        # type: (parts.APartName, parts.AMri, AHasAutosave) -> None
        super(IocStatusPart, self).__init__(name)
        # Hooks
        self.dir1 = None
        self.dir2 = None
        self.dir = ""
        self.controller_mri = mri
        self.has_autosave = has_autosave
        self.register_hooked(hooks.InitHook, self.init_handler)

        elements = OrderedDict()
        elements["module"] = StringArrayMeta("Module",
                                             tags=[Widget.TEXTUPDATE.tag()])
        elements["path"] = StringArrayMeta("Path",
                                           tags=[Widget.TEXTUPDATE.tag()])

        self.dependencies = TableMeta("Modules which this IOC depends on",
                                      tags=[Widget.TABLE.tag()],
                                      writeable=False,
                                      elements=elements).create_attribute_model(
            {"module": [], "path": []})
        if has_autosave:
            self.autosave_pv = CAStringPart("autosaveStatus",
                                            description="status of Autosave",
                                            rbv="%s:SRSTATUS" % name)

    @add_call_types
    def init_handler(self, context):
        # type: (hooks.AContext) -> None
        controller = context.get_controller(self.controller_mri)
        if self.has_autosave:
            controller.add_part(self.autosave_pv)
        subscribe_ver = Subscribe(path=[self.controller_mri, "currentVersion"])
        subscribe_ver.set_callback(self.version_updated)
        controller.handle_request(subscribe_ver).wait()
        subscribe_dir1 = Subscribe(path=[self.controller_mri, "iocDirectory1"])
        subscribe_dir1.set_callback(self.set_dir1)
        controller.handle_request(subscribe_dir1).wait()
        subscribe_dir2 = Subscribe(path=[self.controller_mri, "iocDirectory2"])
        subscribe_dir2.set_callback(self.set_dir2)
        controller.handle_request(subscribe_dir2).wait()

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(IocStatusPart, self).setup(registrar)
        registrar.add_attribute_model("dependencies", self.dependencies)

    def version_updated(self, update):
        self.dls_version = update.value["value"]
        if update.value["value"] == "Work":
            message = "IOC running from work area"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
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
        if os.path.isdir(self.dir):
            with open(release_file, 'r') as release:
                dep_list = release.readlines()
                dep_list = [dep.strip('\n') for dep in dep_list if
                            not dep.startswith('#')]
                for dep in dep_list:
                    dep_split = dep.replace(' ', '').split('=')
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
