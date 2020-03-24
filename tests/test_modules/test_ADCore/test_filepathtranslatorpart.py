import unittest
from mock import MagicMock, call
from malcolm.core import PartRegistrar
from malcolm.modules.ADCore.parts import FilepathTranslatorPart
from malcolm.modules.ADCore.infos import FilePathTranslatorInfo
#from annotypes import Anno, add_call_types


class TestFilePathTranslatorPart(unittest.TestCase):

    def setUp(self):
        self.o = FilepathTranslatorPart("winpath", "C")

    def test_setup(self):
        registrar = MagicMock(spec=PartRegistrar)
        self.o.setup(registrar)
        
        assert registrar.add_attribute_model.mock_calls == [
            call('windowsDriveLetter', self.o.windows_drive_letter, 
                self.o.windows_drive_letter.set_value),
            call('pathPrefix', self.o.path_prefix, self.o.path_prefix.set_value)
        ]

        assert self.o.windows_drive_letter.value == "C"
        assert self.o.path_prefix.value == "/dls"

    def test_report(self):
        part_info = dict(anyname=[self.o.on_report_status()])
        win_path = FilePathTranslatorInfo.translate_filepath(
            part_info, "/dls/directory"
        )
        assert win_path == "C:\\directory"