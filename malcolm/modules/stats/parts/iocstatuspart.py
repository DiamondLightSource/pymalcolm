from malcolm.modules.builtin import parts, hooks, infos
from malcolm.core import Subscribe, ChoiceMeta, TableMeta, StringMeta, \
    StringArrayMeta, Widget, PartRegistrar, Part
from malcolm.core.alarm import AlarmSeverity, Alarm
from malcolm.modules.ca.parts import CAStringPart

import os
import subprocess
from collections import OrderedDict

from annotypes import add_call_types, Anno

epics_logo_svg = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="100px" height="50px" viewBox="0 0 100 50" xml:space="preserve">
<g id="logo" transform="scale(0.1, 0.1) translate(-160, -200)">
<path id="S" fill="#69ccff" d="M880.5,474.714l24.796-29.844c13.879,11.817,31.589,20.094,47.529,20.094   c18.003,0,26.866-7.098,26.866-18.622c0-12.118-10.922-15.954-27.753-23.056l-25.089-10.628   c-19.785-7.985-38.679-24.537-38.679-52.604c0-31.927,28.343-57.334,68.493-57.334c22.141,0,45.46,8.863,61.998,25.407   l-22.143,27.485c-12.691-9.751-24.504-15.359-39.855-15.359c-15.057,0-24.511,6.496-24.511,17.438   c0,11.817,12.704,15.954,29.23,22.751l24.795,10.047c23.333,9.461,38.089,25.122,38.089,52.31   c0,31.915-26.573,59.693-72.621,59.693C926.557,502.493,899.988,493.031,880.5,474.714"/>
<path id="C" fill="#69ccff" d="M720.193,403.782c0-63.822,42.208-101.057,90.926-101.057c24.796,0,44.865,11.821,57.849,25.118   l-23.018,27.774c-9.742-8.867-20.073-15.359-33.949-15.359c-26.272,0-47.228,23.336-47.228,62.057   c0,39.595,18.295,62.65,46.63,62.65c15.653,0,28.042-7.985,37.496-18.028l23.03,27.185c-15.945,18.617-37.211,28.372-62.291,28.372   C760.934,502.493,720.193,468.503,720.193,403.782"/>
<rect id="I" x="640.47" y="306.263" fill="#69ccff" width="43.399" height="192.687"/>
<path id="P" fill="#69ccff" d="M529.165,399.056c23.905,0,35.422-10.641,35.422-30.731c0-20.095-12.992-27.486-36.61-27.486   h-20.076v58.217H529.165z M464.518,306.263h66.115c42.215,0,76.456,15.373,76.456,62.062c0,45.212-34.536,65.31-75.275,65.31   h-23.913v65.311h-43.383V306.263z"/>
<polygon id="E" fill="#69ccff" points="302.721,306.263 302.721,498.95 426.121,498.95 426.121,462.304 346.117,462.304    346.117,417.966 411.651,417.966 411.651,381.617 346.117,381.617 346.117,342.909 423.166,342.909 423.166,306.263  "/>
<polygon id="signe" fill="#69ccff" points="892.313,531.786 892.313,645.119 853.5,645.119 853.5,531.786 721.535,531.786    721.535,645.119 682.819,645.119 682.819,531.786 302.723,531.786 302.723,683.702 434.676,683.702 434.676,570.368    473.495,570.368 473.495,683.702 605.444,683.702 605.444,570.368 644.246,570.368 644.246,683.702 1024.268,683.702    1024.268,531.786  "/>
</g>
</svg
"""

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
        self.dir1 = ""
        self.dir2 = ""
        self.dir = ""
        self.controller_mri = mri
        self.has_autosave = has_autosave
        self.register_hooked(hooks.InitHook, self.init_handler)

        # self.available_versions = ChoiceMeta(
        #     "Available IOC versions (for same EPICS base)", writeable=True,
        #     choices=['unknown'],
        #     tags=[Widget.COMBO.tag()]).create_attribute_model('unknown')

        self.epics_logo = StringMeta("block logo", [
            Widget.ICON.tag()]).create_attribute_model(epics_logo_svg)

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
        # subscribe_epics = Subscribe(path=[self.controller_mri, "epicsVersion"])
        # subscribe_epics.set_callback(self.check_available_versions)
        # controller.handle_request(subscribe_epics).wait()
        subscribe_dir1 = Subscribe(path=[self.controller_mri, "iocDirectory1"])
        subscribe_dir1.set_callback(self.set_dir1)
        controller.handle_request(subscribe_dir1).wait()
        subscribe_dir2 = Subscribe(path=[self.controller_mri, "iocDirectory2"])
        subscribe_dir2.set_callback(self.set_dir2)
        controller.handle_request(subscribe_dir2).wait()

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(IocStatusPart, self).setup(registrar)
        # registrar.add_attribute_model("availableVersions",
        #                               self.available_versions,
        #                               self.configure_ioc)
        registrar.add_attribute_model("epicsLogo",
                                      self.epics_logo)
        registrar.add_attribute_model("dependencies", self.dependencies)

    def version_updated(self, update):
        self.dls_version = update.value["value"]
        if update.value["value"] == "Work":
            message = "IOC running from work area"
            alarm = Alarm(message=message, severity=AlarmSeverity.MINOR_ALARM)
            self.registrar.report(infos.HealthInfo(alarm))
        # elif update.value["value"] in self.available_versions.meta.choices:
        #     self.available_versions.set_value(update.value["value"])

    # def check_available_versions(self, update):
    #     epics_ver = None
    #     if len(update.value["value"]) > 15:
    #         epics_ver = update.value["value"][6:16]
    #     if epics_ver is not None and epics_ver in os.listdir('/dls_sw/prod'):
    #         ioc_name = self.name.split('-')
    #         self.ioc_prod_root = '/dls_sw/prod/%s/ioc/%s/%s' % (
    #             epics_ver, ioc_name[0], self.name)
    #         prod_versions = os.listdir(self.ioc_prod_root)
    #         self.available_versions.meta.set_choices(prod_versions)
    #         if self.dls_version in prod_versions:
    #             self.available_versions.set_value(self.dls_version)

    def set_dir1(self, update):
        self.dir1 = update.value["value"]
        if self.dir1 != "" and self.dir2 != "":
            self.dir = self.dir1 + self.dir2
            self.parse_release()

    def set_dir2(self, update):
        self.dir2 = update.value["value"]
        if self.dir1 != "" and self.dir2 != "":
            self.dir = self.dir1 + self.dir2
            self.parse_release()

    def parse_release(self):
        release_file = os.path.join(self.dir, 'configure', 'RELEASE')
        dependencies = OrderedDict()
        dependency_table = OrderedDict()
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

    # The world isn't ready for this yet
    # def configure_ioc(self, version):
    #     bin_path = os.path.join(self.ioc_prod_root, version, 'bin',
    #                             'linux-x86_64', 'st%s.sh' % self.name)
    #     if os.path.exists(bin_path):
    #         subprocess.call(["configure-ioc", "e", self.name, bin_path])
    #     check = subprocess.check_output(["configure-ioc", "s", "-p", self.name])
    #     if check.strip('\n') == bin_path:
    #         self.available_versions.set_value(version)
    #     else:
    #         raise Exception("configure-ioc call failed: %s" % check)
