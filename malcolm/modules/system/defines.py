import re

from annotypes import Anno, add_call_types
from malcolm.modules.builtin.defines import Define, ADefine, AName

with Anno("name of yaml file (used to get BL prefix)"):
    AYamlName = str

with Anno("path to redirect table"):
    ARedirectPath = str

@add_call_types
def redirector_iocs(name, yamlname, file_path="/dls_sw/prod/etc/redirector/redirect_table"):
    # type: (AName, AYamlName, ARedirectPath) -> ADefine
    bl_prefix = yamlname.split("-")[0]
    with open(file_path, 'r') as redirector:
        table = redirector.read()
        bl_iocs = re.findall(bl_prefix + "-[A-Z][A-Z]-IOC-[0-9][0-9] ",
                             table)
    for ind, ioc in enumerate(bl_iocs):
        bl_iocs[ind] = ioc.strip()
    return Define(name, bl_iocs)