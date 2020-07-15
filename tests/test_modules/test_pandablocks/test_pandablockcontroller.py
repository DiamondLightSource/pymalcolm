import unittest
from collections import OrderedDict

from mock import ANY, Mock

from malcolm.core import (
    Alarm,
    BooleanMeta,
    ChoiceMeta,
    NumberMeta,
    Process,
    Queue,
    StringMeta,
    Subscribe,
    TimeStamp,
)
from malcolm.modules.pandablocks.controllers.pandablockcontroller import (
    PandABlockController,
)
from malcolm.modules.pandablocks.pandablocksclient import BlockData, FieldData


class PandABoxBlockMakerTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.process = Process()
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_block_fields_adder(self):
        fields = OrderedDict()
        block_data = BlockData(2, "Adder description", fields)
        fields["INPA"] = FieldData("pos_mux", "", "Input A", ["A.OUT", "B.OUT"])
        fields["INPB"] = FieldData("pos_mux", "", "Input B", ["A.OUT", "B.OUT"])
        fields["DIVIDE"] = FieldData(
            "param", "enum", "Divide output", ["/1", "/2", "/4"]
        )
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        fields["HEALTH"] = FieldData("read", "enum", "What's wrong", ["OK", "Very Bad"])

        o = PandABlockController(self.client, "MRI", "ADDER1", block_data, "/docs")
        self.process.add_controller(o)
        b = self.process.block_view("MRI:ADDER1")

        assert list(b) == [
            "meta",
            "health",
            "icon",
            "label",
            "help",
            "inputs",
            "inpa",
            "inpb",
            "parameters",
            "divide",
            "outputs",
            "out",
        ]

        group = b.inputs
        assert group.meta.tags == ["widget:group", "config:1"]

        inpa = b.inpa
        assert inpa.meta.writeable is True
        assert inpa.meta.typeid == ChoiceMeta.typeid
        assert inpa.meta.tags == [
            "group:inputs",
            "sinkPort:int32:ZERO",
            "widget:combo",
            "config:1",
        ]
        assert inpa.meta.choices == ["A.OUT", "B.OUT"]
        inpa.put_value("A.OUT")
        self.client.set_field.assert_called_once_with("ADDER1", "INPA", "A.OUT")
        self.client.reset_mock()

        divide = b.divide
        assert divide.meta.writeable is True
        assert divide.meta.typeid == ChoiceMeta.typeid
        assert divide.meta.tags == ["group:parameters", "widget:combo", "config:1"]
        assert divide.meta.choices == ["/1", "/2", "/4"]

        out = b.out
        assert out.meta.writeable is False
        assert out.meta.typeid == NumberMeta.typeid
        assert out.meta.dtype == "int32"
        assert out.meta.tags == [
            "group:outputs",
            "sourcePort:int32:ADDER1.OUT",
            "widget:textupdate",
        ]

        queue = Queue()
        subscribe = Subscribe(path=["MRI:ADDER1", "out"], delta=True)
        subscribe.set_callback(queue.put)
        o.handle_request(subscribe)
        delta = queue.get(timeout=1)
        assert delta.changes[0][1]["value"] == 0

        ts = TimeStamp()
        o.handle_changes({"OUT": "145"}, ts)
        delta = queue.get(timeout=1)
        assert delta.changes == [
            [["value"], 145],
            [["timeStamp"], ts],
        ]

        subscribe = Subscribe(path=["MRI:ADDER1", "health"], delta=True)
        subscribe.set_callback(queue.put)
        o.handle_request(subscribe)
        delta = queue.get(timeout=1)
        assert delta.changes[0][1]["value"] == "OK"

        ts = TimeStamp()
        o.handle_changes({"HEALTH": "Very Bad"}, ts)
        delta = queue.get(timeout=1)
        assert delta.changes == [
            [["value"], "Very Bad"],
            [["alarm"], Alarm.major("Very Bad")],
            [["timeStamp"], ts],
        ]
        o.handle_changes({"HEALTH": "OK"}, ts)
        delta = queue.get(timeout=1)
        assert delta.changes == [
            [["value"], "OK"],
            [["alarm"], Alarm.ok],
            [["timeStamp"], ts],
        ]

    def test_block_fields_pulse(self):
        fields = OrderedDict()
        block_data = BlockData(4, "Pulse description", fields)
        fields["DELAY"] = FieldData("time", "", "Time", [])
        fields["INP"] = FieldData("bit_mux", "", "Input", ["ZERO", "X.OUT", "Y.OUT"])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        fields["ERR_PERIOD"] = FieldData("read", "bit", "Error", [])

        o = PandABlockController(self.client, "MRI", "PULSE2", block_data, "/docs")
        self.process.add_controller(o)
        b = self.process.block_view("MRI:PULSE2")

        assert list(b) == [
            "meta",
            "health",
            "icon",
            "label",
            "help",
            "parameters",
            "delay",
            "delayUnits",
            "inputs",
            "inp",
            "inpDelay",
            "outputs",
            "out",
            "readbacks",
            "errPeriod",
        ]

        assert b.meta.label == "Pulse description 2"
        assert b.label.value == "Pulse description 2"

        # check setting label
        b.label.put_value("A new label")
        assert b.meta.label == "A new label"
        assert b.label.value == "A new label"
        self.client.set_field.assert_called_once_with(
            "*METADATA", "LABEL_PULSE2", "A new label"
        )
        self.client.set_field.reset_mock()

        # check updated with nothing
        o.handle_changes(dict(LABEL=""), ts=TimeStamp())
        assert b.meta.label == "Pulse description 2"
        assert b.label.value == "Pulse description 2"
        self.client.set_field.assert_not_called()

        # check updated with something from the server
        o.handle_changes(dict(LABEL="A server label"), ts=TimeStamp())
        assert b.meta.label == "A server label"
        assert b.label.value == "A server label"
        self.client.set_field.assert_not_called()

        help = b.help
        assert help.value == "/docs/build/pulse_doc.html"

        delay = b.delay
        assert delay.meta.writeable is True
        assert delay.meta.typeid == NumberMeta.typeid
        assert delay.meta.dtype == "float64"
        assert delay.meta.tags == ["group:parameters", "widget:textinput", "config:2"]

        units = b.delayUnits
        assert units.meta.writeable is True
        assert units.meta.typeid == ChoiceMeta.typeid
        assert units.meta.tags == ["group:parameters", "widget:combo", "config:1"]
        assert units.meta.choices == ["s", "ms", "us"]

        inp = b.inp
        assert inp.meta.writeable is True
        assert inp.meta.typeid == ChoiceMeta.typeid
        assert inp.meta.tags == [
            "group:inputs",
            "sinkPort:bool:ZERO",
            "widget:combo",
            "badgevalue:plus:inpDelay:MRI:PULSE2",
            "config:1",
        ]
        assert inp.meta.choices == ["ZERO", "X.OUT", "Y.OUT"]

        delay = b.inpDelay
        assert delay.meta.writeable is True
        assert delay.meta.typeid == NumberMeta.typeid
        assert delay.meta.dtype == "uint8"
        assert delay.meta.tags == ["group:inputs", "widget:textinput", "config:1"]

        out = b.out
        assert out.meta.writeable is False
        assert out.meta.typeid == BooleanMeta.typeid
        assert out.meta.tags == [
            "group:outputs",
            "sourcePort:bool:PULSE2.OUT",
            "widget:led",
        ]

        err = b.errPeriod
        assert err.meta.writeable is False
        assert err.meta.typeid == BooleanMeta.typeid
        assert err.meta.tags == ["group:readbacks", "widget:led"]

        queue = Queue()
        subscribe = Subscribe(path=["MRI:PULSE2", "inp"], delta=True)
        subscribe.set_callback(queue.put)
        o.handle_request(subscribe)
        delta = queue.get()
        assert delta.changes[0][1]["value"] == "ZERO"

        ts = TimeStamp()
        o.handle_changes({"INP": "X.OUT"}, ts)
        delta = queue.get()
        assert delta.changes == [
            [["value"], "X.OUT"],
            [["timeStamp"], ts],
            [
                ["meta", "tags"],
                [
                    "group:inputs",
                    "sinkPort:bool:ZERO",
                    "widget:combo",
                    "badgevalue:plus:inpDelay:MRI:PULSE2",
                    "config:1",
                    "linkedvalue:out:MRI:X",
                ],
            ],
        ]

    def test_block_fields_lut(self):
        fields = OrderedDict()
        block_data = BlockData(8, "Lut description", fields)
        fields["FUNC"] = FieldData("param", "lut", "Function", [])

        o = PandABlockController(self.client, "MRI", "LUT3", block_data, "/docs")
        self.process.add_controller(o)
        b = self.process.block_view("MRI:LUT3")

        func = b.func
        assert func.meta.writeable is True
        assert func.meta.typeid == StringMeta.typeid
        assert func.meta.tags == ["group:parameters", "widget:textinput", "config:1"]

        queue = Queue()
        subscribe = Subscribe(path=["MRI:LUT3"], delta=True)
        subscribe.set_callback(queue.put)
        o.handle_request(subscribe)
        delta = queue.get()
        assert delta.changes[0][1]["func"]["value"] == ""
        assert '<path id="OR"' in delta.changes[0][1]["icon"]["value"]

        # This is the correct FUNC.RAW value for !A&!B&!C&!D&!E
        self.client.get_field.return_value = "1"
        ts = TimeStamp()
        o.handle_changes({"FUNC": "!A&!B&!C&!D&!E"}, ts)
        self.client.get_field.assert_called_once_with("LUT3", "FUNC.RAW")
        delta = queue.get()
        assert delta.changes == [
            [["func", "value"], "!A&!B&!C&!D&!E"],
            [["func", "timeStamp"], ts],
            [["icon", "value"], ANY],
            [["icon", "timeStamp"], ts],
        ]
        assert '<path id="OR"' not in delta.changes[2][1]
