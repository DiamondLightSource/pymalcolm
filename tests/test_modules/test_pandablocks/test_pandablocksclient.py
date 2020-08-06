import unittest
from collections import OrderedDict

from mock import Mock, call

from malcolm.modules.pandablocks.pandablocksclient import (
    BlockData,
    FieldData,
    PandABlocksClient,
)


class PandABoxControlTest(unittest.TestCase):
    def setUp(self):
        self.c = PandABlocksClient("h", "p")

    def start(self, messages=None):
        self.socket = Mock()
        if isinstance(messages, list):
            self.socket.recv.side_effect = [item.encode("utf-8") for item in messages]
        elif messages:
            self.socket.recv.side_effect = [messages.encode("utf-8")]

        def socket_cls():
            return self.socket

        self.c.start(socket_cls=socket_cls)

    def tearDown(self):
        if self.c.started:
            self.c.stop()

    def test_multiline_response_good(self):
        messages = ["!TTLIN 6\n", "!OUTENC 4\n!CAL", "C 2\n.\nblah"]
        self.start(messages)
        resp = list(self.c.send_recv(""))
        self.c.stop()
        expected = ["TTLIN 6", "OUTENC 4", "CALC 2"]
        assert resp == expected

    def test_two_resp(self):
        messages = ["OK =mm\n", "OK =232\n"]
        self.start(messages)
        assert self.c.send_recv("") == "OK =mm"
        assert self.c.send_recv("") == "OK =232"

    def test_bad_good(self):
        messages = ["ERR Invalid bit value\n", "OK =232\n"]
        self.start(messages)
        with self.assertRaises(ValueError):
            self.c.send_recv("")
        assert self.c.send_recv("") == "OK =232"

    def test_block_data(self):
        messages = [
            "!TTLIN 6\n!TTLOUT 10\n.\n",
            "OK =TTL input\n",
            "OK =TTL output\n",
            "!VAL 1 ext_out funny\n!TERM 0 param enum\n.\n",
            "!VAL 0 bit_mux\n.\n",
            "OK =TTL termination\n",
            "OK =TTL input value\n",
            "!High-Z\n!50-Ohm\n.\n",
            "!No\n!Value\n.\n",
            "OK =TTL output value\n",
            "!ZERO\n!TTLIN1.VAL\n!TTLIN2.VAL\n.\n",
        ]
        self.start(messages)
        block_data = self.c.get_blocks_data()
        self.c.stop()
        assert self.socket.sendall.call_args_list == [
            call(b"*BLOCKS?\n"),
            call(b"*DESC.TTLIN?\n"),
            call(b"*DESC.TTLOUT?\n"),
            call(b"TTLIN.*?\n"),
            call(b"TTLOUT.*?\n"),
            call(b"*DESC.TTLIN.TERM?\n"),
            call(b"*DESC.TTLIN.VAL?\n"),
            call(b"*ENUMS.TTLIN.TERM?\n"),
            call(b"*ENUMS.TTLIN.VAL.CAPTURE?\n"),
            call(b"*DESC.TTLOUT.VAL?\n"),
            call(b"*ENUMS.TTLOUT.VAL?\n"),
        ]
        assert list(block_data) == ["TTLIN", "TTLOUT"]
        in_fields = OrderedDict()
        in_fields["TERM"] = FieldData(
            "param", "enum", "TTL termination", ["High-Z", "50-Ohm"]
        )
        in_fields["VAL"] = FieldData(
            "ext_out", "funny", "TTL input value", ["No", "Value"]
        )
        assert block_data["TTLIN"] == (BlockData(6, "TTL input", in_fields))
        out_fields = OrderedDict()
        out_fields["VAL"] = FieldData(
            "bit_mux", "", "TTL output value", ["ZERO", "TTLIN1.VAL", "TTLIN2.VAL"]
        )
        assert block_data["TTLOUT"] == (BlockData(10, "TTL output", out_fields))

    def test_changes(self):
        messages = [
            """!PULSE0.WIDTH=1.43166e+09
!PULSE1.WIDTH=1.43166e+09
!PULSE2.WIDTH=1.43166e+09
!PULSE3.WIDTH=1.43166e+09
!SEQ1.TABLE<
!PULSE0.INP (error)
!PULSE1.INP (error)
!PULSE2.INP (error)
!PULSE3.INP (error)
.
""",
            """!1
!2
!3
.
""",
        ]
        self.start(messages)
        changes = list(self.c.get_changes(include_errors=True))
        self.c.stop()
        assert self.socket.sendall.call_args_list == [
            call(b"*CHANGES?\n"),
            call(b"SEQ1.TABLE?\n"),
        ]
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
        assert OrderedDict(changes) == expected

    def test_get_pcap_bits_fields(self):
        messages = (
            ["!BITS1 1 ext_out bits\n!BITS0 0 ext_out bits\n.\n"]
            + ["!B%d\n" % i for i in range(32)]
            + [".\n"]
            + ["!B%d\n" % i for i in range(32, 52)]
            + ["!\n" * 12]
            + [".\n"]
        )
        self.start(messages)
        expected = {
            "PCAP.BITS0.CAPTURE": ["B%d" % i for i in range(32)],
            "PCAP.BITS1.CAPTURE": ["B%d" % i for i in range(32, 52)] + [""] * 12,
        }
        assert self.c.get_pcap_bits_fields() == expected
        self.c.stop()
        assert self.socket.sendall.call_args_list == [
            call(b"PCAP.*?\n"),
            call(b"PCAP.BITS0.BITS?\n"),
            call(b"PCAP.BITS1.BITS?\n"),
        ]

    def test_get_field(self):
        messages = "OK =32\n"
        self.start(messages)
        assert self.c.get_field("PULSE0", "WIDTH") == "32"
        self.c.stop()
        self.socket.sendall.assert_called_once_with(b"PULSE0.WIDTH?\n")

    def test_set_field(self):
        messages = "OK\n"
        self.start(messages)
        self.c.set_field("PULSE0", "WIDTH", 0)
        self.c.stop()
        self.socket.sendall.assert_called_once_with(b"PULSE0.WIDTH=0\n")

    def test_set_fields(self):
        messages = "OK\nOK\n"
        self.start(messages)
        self.c.set_fields({"PULSE0.WIDTH": 0, "PULSE0.DELAY": 5})
        self.c.stop()
        assert sorted(self.socket.sendall.call_args_list) == [
            call(b"PULSE0.DELAY=5\n"),
            call(b"PULSE0.WIDTH=0\n"),
        ]

    def test_set_table(self):
        messages = "OK\n"
        self.start(messages)
        self.c.set_table("SEQ1", "TABLE", [1, 2, 3])
        self.c.stop()
        self.socket.sendall.assert_called_once_with(
            b"""SEQ1.TABLE<
1
2
3

"""
        )

    def test_table_fields(self):
        messages = [
            """!31:0    REPEATS
!32:32   USE_INPA
!64:54  STUFF
!38:37   INPB enum
.
""",
            """!None
!First
!Second
.
""",
            "OK =Repeats\n",
            "OK =Use\n",
            "OK =Stuff\n",
            "OK =Inp B\n",
        ]
        self.start(messages)
        fields = self.c.get_table_fields("SEQ1", "TABLE")
        self.c.stop()
        assert self.socket.sendall.call_args_list == [
            call(b"SEQ1.TABLE.FIELDS?\n"),
            call(b"*ENUMS.SEQ1.TABLE[].INPB?\n"),
            call(b"*DESC.SEQ1.TABLE[].REPEATS?\n"),
            call(b"*DESC.SEQ1.TABLE[].USE_INPA?\n"),
            call(b"*DESC.SEQ1.TABLE[].STUFF?\n"),
            call(b"*DESC.SEQ1.TABLE[].INPB?\n"),
        ]
        expected = OrderedDict()
        expected["REPEATS"] = (31, 0, "Repeats", None, False)
        expected["USE_INPA"] = (32, 32, "Use", None, False)
        expected["STUFF"] = (64, 54, "Stuff", None, False)
        expected["INPB"] = (38, 37, "Inp B", ["None", "First", "Second"], False)
        assert fields == expected
