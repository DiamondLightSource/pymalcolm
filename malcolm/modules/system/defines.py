import re

from annotypes import Anno, add_call_types

from malcolm.modules.builtin.defines import ADefine, AName, Define

with Anno("name of yaml file (used to get BL prefix)"):
    AYamlName = str

with Anno("path to redirect table"):
    ARedirectPath = str


@add_call_types
def redirector_iocs(
    name: AName,
    yamlname: AYamlName,
    file_path: ARedirectPath = "/dls_sw/prod/etc/redirector/redirect_table",
) -> ADefine:
    bl_prefix = yamlname.split("-")[0]
    with open(file_path, "r") as redirector:
        table = redirector.read()
        bl_iocs = re.findall(bl_prefix + "-[A-Z][A-Z]-IOC-[0-9][0-9] ", table)
    ioc_list = ""
    for ioc in bl_iocs:
        ioc_list += ioc
    return Define(name, ioc_list)
