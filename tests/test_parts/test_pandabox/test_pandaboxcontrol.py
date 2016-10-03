import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import call, patch

from malcolm.parts.pandabox.pandaboxcontrol import PandABoxControl, BlockData, \
    FieldData
from malcolm.core import Process, SyncFactory


class PandABoxControlTest(unittest.TestCase):
    @patch("malcolm.parts.pandabox.pandaboxcontrol.socket")
    def setUp(self, mock_socket):
        self.p = Process("process", SyncFactory("sf"))
        self.c = PandABoxControl(self.p, "h", "p")

    def test_multiline_response_good(self):
        messages = ["!TTLIN 6\n", "!OUTENC 4\n!CAL", "C 2\n.\nblah"]
        self.c.socket.recv.side_effect = messages
        self.c.start()
        resp = list(self.c.send_recv(""))
        self.c.stop()
        self.c.wait()
        expected = ["TTLIN 6", "OUTENC 4", "CALC 2"]
        self.assertEqual(resp, expected)

    def test_two_resp(self):
        messages = ["OK =mm\n", "OK =232\n"]
        self.c.socket.recv.side_effect = messages
        self.c.start()
        self.assertEqual(self.c.send_recv(""), "OK =mm")
        self.assertEqual(self.c.send_recv(""), "OK =232")

    def test_bad_good(self):
        messages = ["ERR Invalid bit value\n", "OK =232\n"]
        self.c.socket.recv.side_effect = messages
        self.c.start()
        self.assertRaises(ValueError, self.c.send_recv, "")
        self.assertEqual(self.c.send_recv(""), "OK =232")

    def test_block_data(self):
        self.c.socket.recv.side_effect = [
            "!TTLIN 6\n!TTLOUT 10\n.\n",
            "OK =TTL input\n",
            "OK =TTL output\n",
            "!VAL 1 pos_out\n!TERM 0 param enum\n.\n",
            "!VAL 0 bit_mux\n.\n",
            "OK =TTL termination\n",
            "OK =TTL input value\n",
            "!High-Z\n!50-Ohm\n.\n",
            "!Average\n!No\n.\n",
            "OK =TTL output value\n",
            "!ZERO\n!TTLIN1.VAL\n!TTLIN2.VAL\n.\n",
        ]
        self.c.start()
        block_data = self.c.get_blocks_data()
        self.c.stop()
        self.c.wait()
        self.assertEqual(self.c.socket.send.call_args_list, [
            call("*BLOCKS?\n"),
            call("*DESC.TTLIN?\n"),
            call("*DESC.TTLOUT?\n"),
            call("TTLIN.*?\n"),
            call("TTLOUT.*?\n"),
            call("*DESC.TTLIN.TERM?\n"),
            call("*DESC.TTLIN.VAL?\n"),
            call("*ENUMS.TTLIN.TERM?\n"),
            call("*ENUMS.TTLIN.VAL.CAPTURE?\n"),
            call("*DESC.TTLOUT.VAL?\n"),
            call("*ENUMS.TTLOUT.VAL?\n"),
        ])
        self.assertEqual(list(block_data), ["TTLIN", "TTLOUT"])
        in_fields = OrderedDict()
        in_fields["TERM"] = FieldData("param", "enum", "TTL termination",
                                      ["High-Z", "50-Ohm"])
        in_fields["VAL"] = FieldData("pos_out", "", "TTL input value",
                                     ["Average", "No"])
        self.assertEqual(block_data["TTLIN"],
                         BlockData(6, "TTL input", in_fields))
        out_fields = OrderedDict()
        out_fields["VAL"] = FieldData("bit_mux", "", "TTL output value", [
            "ZERO", "TTLIN1.VAL", "TTLIN2.VAL"])
        self.assertEqual(block_data["TTLOUT"],
                         BlockData(10, "TTL output", out_fields))

    def test_changes(self):
        self.c.socket.recv.side_effect = ["""!PULSE0.WIDTH=1.43166e+09
!PULSE1.WIDTH=1.43166e+09
!PULSE2.WIDTH=1.43166e+09
!PULSE3.WIDTH=1.43166e+09
!SEQ1.TABLE<
!PULSE0.INP (error)
!PULSE1.INP (error)
!PULSE2.INP (error)
!PULSE3.INP (error)
.
""","""!1
!2
!3
.
"""]
        self.c.start()
        changes = self.c.get_changes()
        self.c.stop()
        self.c.wait()
        self.assertEqual(self.c.socket.send.call_args_list, [
            call("*CHANGES?\n"), call("SEQ1.TABLE?\n")])
        expected = OrderedDict()
        expected["PULSE0.WIDTH"] = "1.43166e+09"
        expected["PULSE1.WIDTH"] = "1.43166e+09"
        expected["PULSE2.WIDTH"] = "1.43166e+09"
        expected["PULSE3.WIDTH"] = "1.43166e+09"
        expected["SEQ1.TABLE"] = ["1", "2", "3"]
        expected["PULSE0.INP"] = Exception
        expected["PULSE1.INP"] = Exception
        expected["PULSE2.INP"] = Exception
        expected["PULSE3.INP"] = Exception
        self.assertEqual(changes, expected)

    def test_set_field(self):
        self.c.socket.recv.return_value = "OK\n"
        self.c.start()
        self.c.set_field("PULSE0", "WIDTH", 0)
        self.c.stop()
        self.c.wait()
        self.c.socket.send.assert_called_once_with("PULSE0.WIDTH=0\n")

    def test_set_table(self):
        self.c.socket.recv.return_value = "OK\n"
        self.c.start()
        self.c.set_table("SEQ1", "TABLE", [1, 2, 3])
        self.c.stop()
        self.c.wait()
        self.c.socket.send.assert_called_once_with("""SEQ1.TABLE<
1
2
3

""")

    def test_table_fields(self):
        self.c.socket.recv.return_value = """!31:0    REPEATS
!32:32   USE_INPA
!64:54   STUFF
!37:37   INPB
.
"""
        self.c.start()
        fields = self.c.get_table_fields("SEQ1", "TABLE")
        self.c.stop()
        self.c.wait()
        self.c.socket.send.assert_called_once_with("SEQ1.TABLE.FIELDS?\n")
        expected = OrderedDict()
        expected["REPEATS"] = (31, 0)
        expected["USE_INPA"] = (32, 32)
        expected["STUFF"] = (64, 54)
        expected["INPB"] = (37, 37)
        self.assertEqual(fields, expected)
