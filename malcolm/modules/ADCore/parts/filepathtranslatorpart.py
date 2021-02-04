from annotypes import Anno, add_call_types

from malcolm.core import APartName, Part, PartRegistrar, StringMeta, Widget, config_tag
from malcolm.modules import scanning

from ..infos import FilePathTranslatorInfo

drive_letter_desc = "Letter assigned to the windows drive mount"
with Anno(drive_letter_desc):
    ADriveLetter = str
path_prefix_desc = "The first bit of the file path (i.e. /dls for /dls/i18/...)"
with Anno(path_prefix_desc):
    APathPrefix = str
network_prefix_desc = "The path prefix if it is a network mount (e.g. " "//dc" ")"
with Anno(network_prefix_desc):
    ANetworkPrefix = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName


class FilepathTranslatorPart(Part):
    def __init__(
        self,
        name: APartName,
        initial_windows_drive_letter: ADriveLetter,
        initial_path_prefix: APathPrefix = "/dls",
        initial_network_prefix: ANetworkPrefix = "",
    ) -> None:
        super().__init__(name)
        self.windows_drive_letter = StringMeta(
            drive_letter_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
        ).create_attribute_model(initial_windows_drive_letter)
        self.path_prefix = StringMeta(
            path_prefix_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
        ).create_attribute_model(initial_path_prefix)
        self.network_prefix = StringMeta(
            network_prefix_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
        ).create_attribute_model(initial_network_prefix)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.on_report_status)
        # Attributes
        registrar.add_attribute_model(
            "windowsDriveLetter",
            self.windows_drive_letter,
            self.windows_drive_letter.set_value,
        )
        registrar.add_attribute_model(
            "pathPrefix", self.path_prefix, self.path_prefix.set_value
        )
        registrar.add_attribute_model(
            "networkPrefix", self.network_prefix, self.network_prefix.set_value
        )

    @add_call_types
    def on_report_status(self) -> scanning.hooks.UInfos:
        info = FilePathTranslatorInfo(
            self.windows_drive_letter.value,
            self.path_prefix.value,
            self.network_prefix.value,
        )
        return info
