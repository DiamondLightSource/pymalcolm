import unittest

from mock import MagicMock, call

from malcolm.core import PartRegistrar
from malcolm.modules.ADCore.infos import FilePathTranslatorInfo
from malcolm.modules.ADCore.parts import FilepathTranslatorPart


class TestFilePathTranslatorPartLocal(unittest.TestCase):
    def setUp(self):
        self.o = FilepathTranslatorPart("winpath", "C")

    def test_setup(self):
        registrar = MagicMock(spec=PartRegistrar)
        self.o.setup(registrar)

        assert registrar.add_attribute_model.mock_calls == [
            call(
                "windowsDriveLetter",
                self.o.windows_drive_letter,
                self.o.windows_drive_letter.set_value,
            ),
            call("pathPrefix", self.o.path_prefix, self.o.path_prefix.set_value),
            call(
                "networkPrefix", self.o.network_prefix, self.o.network_prefix.set_value
            ),
        ]

        assert self.o.windows_drive_letter.value == "C"
        assert self.o.path_prefix.value == "/dls"
        assert self.o.network_prefix.value == ""

    def test_report_local_mount(self):
        part_info = dict(anyname=[self.o.on_report_status()])
        win_path = FilePathTranslatorInfo.translate_filepath(
            part_info, "/dls/directory"
        )
        assert win_path == "C:\\directory"


class TestFilePathTranslatorPartNetwork(unittest.TestCase):
    def setUp(self):
        self.o = FilepathTranslatorPart("winpath", "", "/dls", "//dc")

    def test_report_network_mount(self):
        part_info = dict(anyname=[self.o.on_report_status()])
        win_path = FilePathTranslatorInfo.translate_filepath(
            part_info, "/dls/directory"
        )
        assert win_path == "\\\\dc\\dls\\directory"
