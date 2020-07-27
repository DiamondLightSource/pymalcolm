import difflib
import unittest
from typing import Dict, List, Tuple

from p4p import Type, Value
from p4p.client.raw import RemoteError
from p4p.client.thread import TimeoutError
from p4p.nt.scalar import ntfloat

from malcolm import __version__
from malcolm.core import Process, Queue
from malcolm.modules.demo.blocks import counter_block, hello_block
from malcolm.modules.pva.blocks import pva_server_block
from malcolm.modules.pva.controllers.pvaconvert import EMPTY

block_meta_tuple = (
    "S",
    "malcolm:core/BlockMeta:1.0",
    [
        ("description", "s"),
        ("tags", "as"),
        ("writeable", "?"),
        ("label", "s"),
        ("fields", "as"),
    ],
)

alarm_tuple = ("S", "alarm_t", [("severity", "i"), ("status", "i"), ("message", "s")])

alarm_ok = {"severity": 0, "status": 0, "message": ""}

ts_tuple = (
    "S",
    "time_t",
    [("secondsPastEpoch", "l"), ("nanoseconds", "i"), ("userTag", "i")],
)

display_tuple = (
    "S",
    "display_t",
    [
        ("limitLow", "d"),
        ("limitHigh", "d"),
        ("description", "s"),
        ("precision", "i"),
        ("units", "s"),
    ],
)

ts_zero = {"secondsPastEpoch": 0, "nanoseconds": 0, "userTag": 0}

health_attribute_tuple = (
    "S",
    "epics:nt/NTScalar:1.0",
    [
        ("value", "s"),
        ("alarm", alarm_tuple),
        ("timeStamp", ts_tuple),
        (
            "meta",
            (
                "S",
                "malcolm:core/StringMeta:1.0",
                [
                    ("description", "s"),
                    ("tags", "as"),
                    ("writeable", "?"),
                    ("label", "s"),
                ],
            ),
        ),
    ],
)

empty_map_meta_tuple: Tuple[str, str, List] = (
    "S",
    "malcolm:core/MapMeta:1.0",
    [("elements", ("S", None, [])), ("required", "as")],
)

empty_method_meta_tuple = (
    "S",
    "malcolm:core/MethodMeta:1.1",
    [
        ("takes", empty_map_meta_tuple),
        ("defaults", ("S", None, [])),
        ("description", "s"),
        ("tags", "as"),
        ("writeable", "?"),
        ("label", "s"),
        ("returns", empty_map_meta_tuple),
    ],
)

empty_method_log_tuple = (
    "S",
    "malcolm:core/MethodLog:1.0",
    [
        ("value", ("S", None, [])),
        ("present", "as"),
        ("alarm", alarm_tuple),
        ("timeStamp", ts_tuple),
    ],
)

empty_method_tuple = (
    "S",
    "malcolm:core/Method:1.1",
    [
        ("took", empty_method_log_tuple),
        ("returned", empty_method_log_tuple),
        ("meta", empty_method_meta_tuple),
    ],
)

empty_map_meta_dict: Dict = {"elements": {}, "required": []}

empty_method_log_dict = {
    "value": {},
    "present": [],
    "alarm": alarm_ok,
    "timeStamp": ts_zero,
}

ntscalar_tuple = (
    "S",
    "epics:nt/NTScalar:1.0",
    [
        ("value", "d"),
        ("alarm", alarm_tuple),
        ("timeStamp", ts_tuple),
        (
            "meta",
            (
                "S",
                "malcolm:core/NumberMeta:1.0",
                [
                    ("dtype", "s"),
                    ("description", "s"),
                    ("tags", "as"),
                    ("writeable", "?"),
                    ("label", "s"),
                    ("display", display_tuple),
                ],
            ),
        ),
    ],
)

counter_block_t = Type(
    [
        ("meta", block_meta_tuple),
        ("health", health_attribute_tuple),
        ("counter", ntscalar_tuple),
        ("delta", ntscalar_tuple),
        ("zero", empty_method_tuple),
        ("increment", empty_method_tuple),
    ],
    "malcolm:core/Block:1.0",
)

counter_dict = {
    "meta": {
        "description": "Hardware Block simulating a single float64 counter",
        "tags": ["version:pymalcolm:%s" % __version__],
        "writeable": True,
        "label": "TESTCOUNTER",
        "fields": ["health", "counter", "delta", "zero", "increment"],
    },
    "health": {
        "value": "OK",
        "alarm": alarm_ok,
        "timeStamp": ts_zero,
        "meta": {
            "description": "Displays OK or an error message",
            "tags": ["widget:textupdate"],
            "writeable": False,
            "label": "Health",
        },
    },
    "counter": {
        "value": 0.0,
        "alarm": alarm_ok,
        "timeStamp": ts_zero,
        "meta": {
            "dtype": "float64",
            "description": "The current value of the counter",
            "tags": ["config:1", "widget:textinput"],
            "writeable": True,
            "label": "Counter",
            "display": {"precision": 8},
        },
    },
    "delta": {
        "value": 1.0,
        "alarm": alarm_ok,
        "timeStamp": ts_zero,
        "meta": {
            "dtype": "float64",
            "description": "The amount to increment() by",
            "tags": ["config:1", "widget:textinput"],
            "writeable": True,
            "label": "Delta",
            "display": {"precision": 8},
        },
    },
    "zero": {
        "took": empty_method_log_dict,
        "returned": empty_method_log_dict,
        "meta": {
            "takes": empty_map_meta_dict,
            "description": "Zero the counter attribute",
            "tags": [],
            "writeable": True,
            "label": "Zero",
            "returns": empty_map_meta_dict,
        },
    },
    "increment": {
        "took": empty_method_log_dict,
        "returned": empty_method_log_dict,
        "meta": {
            "takes": empty_map_meta_dict,
            "description": "Add delta to the counter attribute",
            "tags": [],
            "writeable": True,
            "label": "Increment",
            "returns": empty_map_meta_dict,
        },
    },
}

counter_expected = Value(counter_block_t, counter_dict)

string_meta = "malcolm:core/StringMeta:1.0"
number_meta = "malcolm:core/NumberMeta:1.0"

hello_block_t = Type(
    [
        ("meta", block_meta_tuple),
        ("health", health_attribute_tuple),
        (
            "greet",
            (
                "S",
                "malcolm:core/Method:1.1",
                [
                    (
                        "took",
                        (
                            "S",
                            "malcolm:core/MethodLog:1.0",
                            [
                                ("value", ("S", None, [("name", "s"), ("sleep", "d")])),
                                ("present", "as"),
                                ("alarm", alarm_tuple),
                                ("timeStamp", ts_tuple),
                            ],
                        ),
                    ),
                    (
                        "returned",
                        (
                            "S",
                            "malcolm:core/MethodLog:1.0",
                            [
                                ("value", ("S", None, [("return", "s")])),
                                ("present", "as"),
                                ("alarm", alarm_tuple),
                                ("timeStamp", ts_tuple),
                            ],
                        ),
                    ),
                    (
                        "meta",
                        (
                            "S",
                            "malcolm:core/MethodMeta:1.1",
                            [
                                (
                                    "takes",
                                    (
                                        "S",
                                        "malcolm:core/MapMeta:1.0",
                                        [
                                            (
                                                "elements",
                                                (
                                                    "S",
                                                    None,
                                                    [
                                                        (
                                                            "name",
                                                            (
                                                                "S",
                                                                string_meta,
                                                                [
                                                                    (
                                                                        "description",
                                                                        "s",
                                                                    ),
                                                                    ("tags", "as"),
                                                                    ("writeable", "?"),
                                                                    ("label", "s"),
                                                                ],
                                                            ),
                                                        ),
                                                        (
                                                            "sleep",
                                                            (
                                                                "S",
                                                                number_meta,
                                                                [
                                                                    ("dtype", "s"),
                                                                    (
                                                                        "description",
                                                                        "s",
                                                                    ),
                                                                    ("tags", "as"),
                                                                    ("writeable", "?"),
                                                                    ("label", "s"),
                                                                    (
                                                                        "display",
                                                                        display_tuple,
                                                                    ),
                                                                ],
                                                            ),
                                                        ),
                                                    ],
                                                ),
                                            ),
                                            ("required", "as"),
                                        ],
                                    ),
                                ),
                                ("defaults", ("S", None, [("sleep", "d")])),
                                ("description", "s"),
                                ("tags", "as"),
                                ("writeable", "?"),
                                ("label", "s"),
                                (
                                    "returns",
                                    (
                                        "S",
                                        "malcolm:core/MapMeta:1.0",
                                        [
                                            (
                                                "elements",
                                                (
                                                    "S",
                                                    None,
                                                    [
                                                        (
                                                            "return",
                                                            (
                                                                "S",
                                                                string_meta,
                                                                [
                                                                    (
                                                                        "description",
                                                                        "s",
                                                                    ),
                                                                    ("tags", "as"),
                                                                    ("writeable", "?"),
                                                                    ("label", "s"),
                                                                ],
                                                            ),
                                                        ),
                                                    ],
                                                ),
                                            ),
                                            ("required", "as"),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ),
        ("error", empty_method_tuple),
    ],
    "malcolm:core/Block:1.0",
)

hello_dict = {
    "meta": {
        "description": "Hardware Block with a greet() Method",
        "tags": ["version:pymalcolm:%s" % __version__],
        "writeable": True,
        "label": "TESTHELLO",
        "fields": ["health", "greet", "error"],
    },
    "health": {
        "value": "OK",
        "alarm": alarm_ok,
        "timeStamp": ts_zero,
        "meta": {
            "description": "Displays OK or an error message",
            "tags": ["widget:textupdate"],
            "writeable": False,
            "label": "Health",
        },
    },
    "greet": {
        "took": empty_method_log_dict,
        "returned": empty_method_log_dict,
        "meta": {
            "takes": {
                "elements": {
                    "name": {
                        "description": "The name of the person to greet",
                        "tags": ["widget:textinput"],
                        "writeable": True,
                        "label": "Name",
                    },
                    "sleep": {
                        "dtype": "float64",
                        "description": "Time to wait before returning",
                        "tags": ["widget:textinput"],
                        "writeable": True,
                        "label": "Sleep",
                        "display": {"precision": 8},
                    },
                },
                "required": ["name"],
            },
            "defaults": {"sleep": 0.0},
            "description": (
                "Optionally sleep <sleep> seconds, then return a greeting to <name>"
            ),
            "tags": ["method:return:unpacked"],
            "writeable": True,
            "label": "Greet",
            "returns": {
                "elements": {
                    "return": {
                        "description": "The manufactured greeting",
                        "tags": ["widget:textupdate"],
                        "writeable": False,
                        "label": "Return",
                    }
                },
                "required": ["return"],
            },
        },
    },
    "error": {
        "took": empty_method_log_dict,
        "returned": empty_method_log_dict,
        "meta": {
            "takes": empty_map_meta_dict,
            "description": "Raise an error",
            "tags": [],
            "writeable": True,
            "label": "Error",
            "returns": empty_map_meta_dict,
        },
    },
}

hello_expected = Value(hello_block_t, hello_dict)


# These tests need a server running
class TestPVAServer(unittest.TestCase):
    SEQ = 0

    def setUp(self):
        TestPVAServer.SEQ += 1
        self.process = Process("proc%s" % TestPVAServer.SEQ)
        self.hello = hello_block(mri="TESTHELLO")[-1]
        self.process.add_controller(self.hello)
        self.counter = counter_block(mri="TESTCOUNTER")[-1]
        self.process.add_controller(self.counter)
        self.server = pva_server_block(mri="PVA")[-1]
        self.process.add_controller(self.server)
        self.process.start()
        self.addCleanup(self.process.stop, timeout=2)
        self.ctxt = self.make_pva_context(unwrap=False)

    def make_pva_context(self, *args, **kwargs):
        from p4p.client.cothread import Context

        ctxt = Context("pva", *args, **kwargs)
        self.addCleanup(ctxt.close)
        return ctxt

    def assertStructureWithoutTsEqual(self, first, second):
        firstlines = first.splitlines(True)
        secondlines = second.splitlines(True)
        same = len(firstlines) == len(secondlines)

        def linejunk(line):
            # Ignore the timeStamp fields
            split = line.split()
            # ignore timestamps which change
            return len(split) > 1 and split[1] in ("secondsPastEpoch", "nanoseconds")

        for f, s in zip(firstlines, secondlines):
            if not same:
                break
            if not linejunk(s):
                same &= f == s
        if not same:
            diff = "\n" + "".join(difflib.ndiff(firstlines, secondlines, linejunk))
            self.fail(diff)

    # Equivalent to:
    #   pvget TESTCOUNTER -r ""
    def testGetEverything(self):
        counter = self.ctxt.get("TESTCOUNTER")
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))
        self.assertEqual(counter.getID(), "malcolm:core/Block:1.0")
        names = list(counter)
        self.assertEqual(
            names, ["meta", "health", "counter", "delta", "zero", "increment"]
        )
        self.assertEqual(counter.meta.getID(), "malcolm:core/BlockMeta:1.0")
        self.assertEqual(counter.meta.label, "TESTCOUNTER")
        self.assertEqual(counter.meta.fields, names[1:])
        mtype = counter.meta.type()
        fields_code = dict(mtype.items())["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to:
    #   pvget TESTHELLO -r ""
    def testGetEverythingHello(self):
        hello = self.ctxt.get("TESTHELLO")
        self.assertStructureWithoutTsEqual(str(hello), str(hello_expected))

    # Equivalent to:
    #   pvget TESTCOUNTER -r meta.fields
    def testGetSubfield(self):
        counter = self.ctxt.get("TESTCOUNTER", "meta.fields")
        # PvaPy clears the typeid for a substructure
        self.assertEqual(counter.getID(), "structure")
        self.assertEqual(len(counter.items()), 1)
        self.assertEqual(len(counter.meta.items()), 1)
        self.assertEqual(len(counter.meta.fields), 5)
        fields_code = dict(counter.meta.type().items())["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to:
    #   pvget TESTCOUNTER -r junk.thing
    def testGetBadSubfield(self):
        with self.assertRaises(RemoteError):
            self.ctxt.get("TESTCOUNTER", "junk.thing")

    # Equivalent to:
    #   pvget BADCHANNEL -r ""
    def testGetBadChannel(self):
        with self.assertRaises(TimeoutError):
            self.ctxt.get("BADCHANNEL", timeout=1.0)

    # Equivalent to:
    #   pvget TESTCOUNTER.meta -r fields
    def testGetDottedSubfield(self):
        meta = self.ctxt.get("TESTCOUNTER.meta", "fields")
        self.assertEqual(meta.getID(), "structure")
        self.assertEqual(len(meta.items()), 1)
        self.assertEqual(len(meta.fields), 5)
        fields_code = dict(meta.type().aspy()[2])["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to:
    #   pvget TESTCOUNTER.counter -r ""
    def testGetDottedNTScalar(self):
        # Use the one with unwrapping on
        ctxt = self.make_pva_context()
        counter = ctxt.get("TESTCOUNTER.counter")
        self.assertIsInstance(counter, ntfloat)
        self.assertEqual(counter, 0.0)
        self.assertEqual(counter.severity, 0)
        self.assertEqual(counter.raw.getID(), "epics:nt/NTScalar:1.0")

    # Equivalent to:
    #   pvget TESTCOUNTER.counter -r ""
    def testGetDottedNTScalarNoUnwrap(self):
        counter = self.ctxt.get("TESTCOUNTER.counter")
        self.assertEqual(counter.getID(), "epics:nt/NTScalar:1.0")
        self.assertEqual(counter.value, 0.0)
        self.assertEqual(counter.timeStamp.getID(), "time_t")
        self.assertEqual(counter.alarm.getID(), "alarm_t")
        self.assertEqual(counter.alarm.severity, 0)

    def assertCounter(self, value):
        counter = self.counter.block_view().counter.value
        self.assertEqual(counter, value)

    # Equivalent to:
    #   pvput TESTCOUNTER -r "counter.value" counter.value=5
    def testPut(self):
        self.assertCounter(0)
        self.ctxt.put("TESTCOUNTER", {"counter.value": 5}, "counter.value")
        self.assertCounter(5)
        self.ctxt.put("TESTCOUNTER", {"counter.value": 0}, "counter.value")
        self.assertCounter(0)

    # Equivalent to:
    #   pvput TESTCOUNTER.counter 5
    def testPutDotted(self):
        self.assertCounter(0)
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        self.assertCounter(5)
        self.ctxt.put("TESTCOUNTER.counter", 0, "value")
        self.assertCounter(0)

    # Equivalent to:
    #   pvget -m TESTCOUNTER -r ""
    def testMonitorEverythingInitial(self):
        q = Queue()
        m = self.ctxt.monitor("TESTCOUNTER", q.put)
        self.addCleanup(m.close)
        counter = q.get(timeout=1)
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))
        self.assertTrue(
            counter.changedSet().issuperset(
                {"meta.fields", "counter.value", "zero.meta.description"}
            )
        )
        self.assertEqual(counter["counter.value"], 0)
        self.assertEqual(counter["zero.meta.description"], "Zero the counter attribute")
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q.get(timeout=1)
        self.assertEqual(counter.counter.value, 5)
        self.assertEqual(
            counter.changedSet(),
            {
                "counter.value",
                "counter.timeStamp.userTag",
                "counter.timeStamp.secondsPastEpoch",
                "counter.timeStamp.nanoseconds",
            },
        )
        self.ctxt.put("TESTCOUNTER.counter", 0, "value")
        counter = q.get(timeout=1)
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))

    def testTwoMonitors(self):
        assert "TESTCOUNTER" not in self.server._pvs
        # Make first monitor
        q1 = Queue()
        m1 = self.ctxt.monitor("TESTCOUNTER", q1.put)
        self.addCleanup(m1.close)
        counter = q1.get(timeout=1)
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))
        assert len(self.server._pvs["TESTCOUNTER"]) == 1
        # Make a second monitor and check that also fires without making another
        # PV
        ctxt2 = self.make_pva_context()
        q2 = Queue()
        m2 = ctxt2.monitor("TESTCOUNTER", q2.put)
        self.addCleanup(m2.close)
        counter = q2.get(timeout=1)
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))
        assert len(self.server._pvs["TESTCOUNTER"]) == 1
        # Check that a Put fires on both
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q1.get(timeout=1)
        self.assertEqual(counter.counter.value, 5)
        counter = q2.get(timeout=1)
        self.assertEqual(counter.counter.value, 5)

    # Equivalent to:
    #   pvget -m TESTCOUNTER -r meta.fields
    def testMonitorSubfieldInitial(self):
        q = Queue()
        m = self.ctxt.monitor("TESTCOUNTER", q.put, "meta.fields")
        self.addCleanup(m.close)
        counter = q.get(timeout=1)
        self.assertEqual(counter.getID(), "structure")
        # P4P only says leaves have changed
        self.assertEqual(counter.changedSet(), {"meta.fields"})
        self.assertEqual(
            counter.meta.fields, ["health", "counter", "delta", "zero", "increment"]
        )
        fields_code = dict(counter.meta.type().aspy()[2])["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to
    #   pvget -m TESTCOUNTER.counter -r ""
    def testMonitorDotted(self):
        q = Queue()
        m = self.ctxt.monitor("TESTCOUNTER.counter", q.put)
        self.addCleanup(m.close)
        counter: Value = q.get(timeout=1)
        self.assertEqual(counter.getID(), "epics:nt/NTScalar:1.0")
        self.assertTrue(
            counter.changedSet().issuperset(
                {"value", "alarm.severity", "timeStamp.userTag"}
            )
        )
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q.get(timeout=1)
        self.assertEqual(counter.value, 5)
        self.assertEqual(
            counter.changedSet(),
            {
                "value",
                "timeStamp.userTag",
                "timeStamp.secondsPastEpoch",
                "timeStamp.nanoseconds",
            },
        )
        self.ctxt.put("TESTCOUNTER.counter", 0, "value")
        counter = q.get(timeout=1)
        self.assertEqual(counter.value, 0)

    def testRpcRoot(self):
        method = Value(Type([("method", "s")]), dict(method="zero"))
        self.ctxt.rpc("TESTCOUNTER", value=None, request=method)
        self.assertCounter(0)
        method = Value(Type([("method", "s")]), dict(method="increment"))
        ret = self.ctxt.rpc("TESTCOUNTER", EMPTY, method)
        self.assertEqual(ret.tolist(), [])
        self.assertCounter(1)
        method = Value(Type([("method", "s")]), dict(method="zero"))
        self.ctxt.rpc("TESTCOUNTER", EMPTY, method)
        self.assertCounter(0)

    # Equivalent to:
    #   eget -z -s "TESTCOUNTER.zero"
    def testRpcDotted(self):
        self.ctxt.rpc("TESTCOUNTER.zero", EMPTY)
        self.assertCounter(0)
        result = self.ctxt.rpc("TESTCOUNTER.increment", EMPTY)
        self.assertEqual(dict(result.items()), {})
        self.assertCounter(1)
        self.ctxt.rpc("TESTCOUNTER.zero", EMPTY)
        self.assertCounter(0)

    def testRpcArguments(self):
        args = Value(Type([("name", "s")]), dict(name="world"))
        method = Value(Type([("method", "s")]), dict(method="greet"))
        result = self.ctxt.rpc("TESTHELLO", args, method)
        self.assertEqual(dict(result.items()), {"return": "Hello world"})

    def testRpcArgumentsDotted(self):
        args = Value(Type([("name", "s")]), dict(name="me"))
        result = self.ctxt.rpc("TESTHELLO.greet", args)
        self.assertEqual(dict(result.items()), {"return": "Hello me"})

    # Equivalent to:
    #    eget -z -s "TESTHELLO.greet" -a name=me
    def testRpcError(self):
        with self.assertRaises(RuntimeError) as cm:
            self.ctxt.rpc("TESTHELLO.error", EMPTY)
        self.assertEqual(str(cm.exception), "RuntimeError: You called method error()")
