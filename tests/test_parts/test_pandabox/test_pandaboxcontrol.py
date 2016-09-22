import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call, patch

from malcolm.parts.pandabox.pandaboxcontrol import PandABoxControl
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
        expected = ["TTLIN 6", "OUTENC 4", "CALC 2"]
        self.assertEqual(resp, expected)

    def test_two_resp(self):
        messages = ["OK =mm\n", "OK =232\n"]
        self.c.socket.recv.side_effect = messages
        self.c.start()
        self.assertEqual(self.c.send_recv(""), "OK =mm")
        self.assertEqual(self.c.send_recv(""), "OK =232")
        self.c.stop()

    def test_bad_good(self):
        messages = ["ERR Invalid bit value\n", "OK =232\n"]
        self.c.socket.recv.side_effect = messages
        self.c.start()
        self.assertRaises(ValueError, self.c.send_recv, "")
        self.assertEqual(self.c.send_recv(""), "OK =232")
        self.c.stop()

    def test_num_blocks(self):
        self.c.socket.recv.return_value = """!TTLIN 6
!OUTENC 4
!CALC 2
!SRGATE 4
!PCOMP 4
!LUT 8
!TTLOUT 10
!LVDSOUT 2
!ADC 8
!DIV 4
!INENC 4
!COUNTER 8
!ADDER 1
!PCAP 1
!POSENC 4
!LVDSIN 2
!PGEN 2
!QDEC 4
!SEQ 4
!PULSE 4
.
"""
        self.c.start()
        blocks = self.c.get_num_blocks()
        self.c.stop()
        self.c.socket.send.assert_called_once_with("*BLOCKS?\n")
        pretty = ",".join("{}={}".format(k, v) for k, v in blocks.items())
        expected = "TTLIN=6,OUTENC=4,CALC=2,SRGATE=4,PCOMP=4,LUT=8,TTLOUT=10,LVDSOUT=2,ADC=8,DIV=4,INENC=4,COUNTER=8,ADDER=1,PCAP=1,POSENC=4,LVDSIN=2,PGEN=2,QDEC=4,SEQ=4,PULSE=4"
        self.assertEqual(pretty, expected)

    def test_field_data(self):
        self.c.socket.recv.return_value = """!FUNC 0 param lut
!INPA 1 bit_in
!INPB 2 bit_in
!INPC 3 bit_in
!INPD 4 bit_in
!INPE 5 bit_in
!VAL 6 bit_out bit
.
"""
        self.c.start()
        field_data = self.c.get_field_data("LUT")
        self.c.stop()
        self.c.socket.send.assert_called_once_with("LUT.*?\n")
        pretty = ",".join("{}={}:{}".format(k, c, t)
                          for k, (c, t) in field_data.items())
        expected = "FUNC=param:lut,INPA=bit_in:,INPB=bit_in:,INPC=bit_in:,INPD=bit_in:,INPE=bit_in:,VAL=bit_out:bit"
        self.assertEqual(pretty, expected)

    def test_changes(self):
        self.c.socket.recv.return_value = """!PULSE0.WIDTH=1.43166e+09
!PULSE1.WIDTH=1.43166e+09
!PULSE2.WIDTH=1.43166e+09
!PULSE3.WIDTH=1.43166e+09
!PULSE0.INP (error)
!PULSE1.INP (error)
!PULSE2.INP (error)
!PULSE3.INP (error)
.
"""
        self.c.start()
        changes = self.c.get_changes()
        self.c.stop()
        self.c.socket.send.assert_called_once_with("*CHANGES?\n")
        expected = OrderedDict()
        expected["PULSE0.WIDTH"] = "1.43166e+09"
        expected["PULSE1.WIDTH"] = "1.43166e+09"
        expected["PULSE2.WIDTH"] = "1.43166e+09"
        expected["PULSE3.WIDTH"] = "1.43166e+09"
        expected["PULSE0.INP"] = Exception
        expected["PULSE1.INP"] = Exception
        expected["PULSE2.INP"] = Exception
        expected["PULSE3.INP"] = Exception
        self.assertEqual(changes, expected)

    def test_set(self):
        self.c.socket.recv.return_value = "OK\n"
        self.c.start()
        self.c.set_field("PULSE0", "WIDTH", 0)
        self.c.stop()
        self.c.socket.send.assert_called_once_with("PULSE0.WIDTH=0\n")

    def test_bits(self):
        bits = []
        messages = []
        for i in range(4):
            names = []
            for j in range(32):
                names.append("field {}".format(i * 32 + j))
            bits += names
            messages += ["!{}\n".format(f) for f in names]
            messages.append(".\n")
        self.c.socket.recv.side_effect = messages
        self.c.start()
        resp = self.c.get_bits()
        self.c.stop()
        self.assertEqual(resp, bits)

    def test_positions(self):
        positions = []
        for j in range(32):
            positions.append("field {}".format(j))
        messages = ["!{}\n".format(f) for f in positions]
        messages.append(".\n")
        self.c.socket.recv.side_effect = messages
        self.c.start()
        resp = self.c.get_positions()
        self.c.stop()
        self.assertEqual(resp, positions)

    def test_enum_labels(self):
        labels = ["High-Z", "50-Ohm"]
        self.c.socket.recv.side_effect = ["!High-Z\n!50-Ohm\n.\n"]
        self.c.start()
        resp = self.c.get_enum_labels("TTLIN1", "TERM")
        self.c.stop()
        self.assertEqual(resp, labels)
        self.c.socket.send.assert_called_once_with("*ENUMS.TTLIN1.TERM?\n")
