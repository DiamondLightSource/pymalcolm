from __future__ import print_function

# import logging
# logging.basicConfig(level=logging.DEBUG)

import difflib
import unittest

from p4p.nt.scalar import ntfloat
from p4p.client.thread import TimeoutError
from p4p import Value, Type
from p4p.client.raw import RemoteError


from malcolm.compat import maybe_import_cothread
from malcolm.core import Process, Queue
from malcolm.modules.demo.blocks import hello_block, counter_block
from malcolm.modules.pva.blocks import pva_server_block
from malcolm.modules.pva.controllers.pvaconvert import EMPTY


# Set to true if running against old server
PVAPY = False


block_meta_tuple = ('S', 'malcolm:core/BlockMeta:1.0', [
    ('description', 's'),
    ('tags', 'as'),
    ('writeable', '?'),
    ('label', 's'),
    ('fields', 'as')
])

alarm_tuple = ('S', 'alarm_t', [
    ('severity', 'i'),
    ('status', 'i'),
    ('message', 's')
])

alarm_ok = {
    'severity': 0,
    'status': 0,
    'message': ''
}

ts_tuple = ('S', 'time_t', [
    ('secondsPastEpoch', 'l'),
    ('nanoseconds', 'i'),
    ('userTag', 'i')
])

ts_zero = {
    'secondsPastEpoch': 0,
    'nanoseconds': 0,
    'userTag': 0
}

health_attribute_tuple = ('S', 'epics:nt/NTScalar:1.0', [
    ('value', 's'),
    ('alarm', alarm_tuple),
    ('timeStamp', ts_tuple),
    ('meta', ('S', 'malcolm:core/StringMeta:1.0', [
        ('description', 's'),
        ('tags', 'as'),
        ('writeable', '?'),
        ('label', 's')
    ]))
])

if PVAPY:
    # PvaPy can't do empty structures, so suppress elements
    empty_map_meta_tuple = ('S', 'malcolm:core/MapMeta:1.0', [
        ('required', 'as'),
    ])
    empty_method_tuple = ('S', 'malcolm:core/Method:1.0', [
        ('takes', empty_map_meta_tuple),
        ('description', 's'),
        ('tags', 'as'),
        ('writeable', '?'),
        ('label', 's'),
        ('returns', empty_map_meta_tuple)
    ])
else:
    empty_map_meta_tuple = ('S', 'malcolm:core/MapMeta:1.0', [
        ('elements', ('S', None, [])),
        ('required', 'as'),
    ])
    empty_method_tuple = ('S', 'malcolm:core/Method:1.0', [
        ('takes', empty_map_meta_tuple),
        ('defaults', ('S', None, [])),
        ('description', 's'),
        ('tags', 'as'),
        ('writeable', '?'),
        ('label', 's'),
        ('returns', empty_map_meta_tuple)
    ])

if PVAPY:
    # PvaPy can't do empty structures, so suppress elements
    empty_map_meta_dict = {
        'required': []
    }
else:
    empty_map_meta_dict = {
        'elements': {},
        'required': []
    }

counter_block_t = Type([
    ('meta', block_meta_tuple),
    ('health', health_attribute_tuple),
    ('counter', ('S', 'epics:nt/NTScalar:1.0', [
        ('value', 'd'),
        ('alarm', alarm_tuple),
        ('timeStamp', ts_tuple),
        ('meta', ('S', 'malcolm:core/NumberMeta:1.0', [
            ('dtype', 's'),
            ('description', 's'),
            ('tags', 'as'),
            ('writeable', '?'),
            ('label', 's')
        ])),
    ])),
    ('zero', empty_method_tuple),
    ('increment', empty_method_tuple)
], 'malcolm:core/Block:1.0')

counter_dict = {
    'meta': {
        'description': 'Hardware Block simulating a single float64 counter',
        'tags': [],
        'writeable': True,
        'label': 'TESTCOUNTER',
        'fields': ['health', 'counter', 'zero', 'increment']
    },
    'health': {
        'value': "OK",
        'alarm': alarm_ok,
        'timeStamp': ts_zero,
        'meta': {
            'description': 'Displays OK or an error message',
            'tags': ['widget:textupdate'],
            'writeable': False,
            'label': 'Health'
        }
    },
    'counter': {
        'value': 0.0,
        'alarm': alarm_ok,
        'timeStamp': ts_zero,
        'meta': {
            'dtype': 'float64',
            'description': 'The current value of the counter',
            'tags': ['config:1'],
            'writeable': True,
            'label': 'Counter'
        }
    },
    'zero': {
        'takes': empty_map_meta_dict,
        'description': 'Zero the counter attribute',
        'tags': [],
        'writeable': True,
        'label': 'Zero',
        'returns': empty_map_meta_dict
    },
    'increment': {
        'takes': empty_map_meta_dict,
        'description': 'Add one to the counter attribute',
        'tags': [],
        'writeable': True,
        'label': 'Increment',
        'returns': empty_map_meta_dict
    }
}

counter_expected = Value(counter_block_t, counter_dict)

hello_block_t = Type([
    ('meta', block_meta_tuple),
    ('health', health_attribute_tuple),
    ('greet', ('S', 'malcolm:core/Method:1.0', [
        ('takes', ('S', 'malcolm:core/MapMeta:1.0', [
            ('elements', ('S', None, [
                ('name', ('S', 'malcolm:core/StringMeta:1.0', [
                    ('description', 's'),
                    ('tags', 'as'),
                    ('writeable', '?'),
                    ('label', 's')
                ])),
                ('sleep', ('S', 'malcolm:core/NumberMeta:1.0', [
                    ('dtype', 's'),
                    ('description', 's'),
                    ('tags', 'as'),
                    ('writeable', '?'),
                    ('label', 's')
                ]))
            ])),
            ('required', 'as')
        ])),
        ('defaults', ('S', None, [
            ('sleep', 'd')
        ])),
        ('description', 's'),
        ('tags', 'as'),
        ('writeable', '?'),
        ('label', 's'),
        ('returns', ('S', 'malcolm:core/MapMeta:1.0', [
            ('elements', ('S', None, [
                ('return', ('S', 'malcolm:core/StringMeta:1.0', [
                    ('description', 's'),
                    ('tags', 'as'),
                    ('writeable', '?'),
                    ('label', 's')
                ])),
            ])),
            ('required', 'as')
        ])),
    ])),
    ('error', empty_method_tuple)
], 'malcolm:core/Block:1.0')

hello_dict = {
    'meta': {
        'description': 'Hardware Block with a greet() Method',
        'tags': [],
        'writeable': True,
        'label': 'TESTHELLO',
        'fields': ['health', 'greet', 'error']
    },
    'health': {
        'value': "OK",
        'alarm': alarm_ok,
        'timeStamp': ts_zero,
        'meta': {
            'description': 'Displays OK or an error message',
            'tags': ['widget:textupdate'],
            'writeable': False,
            'label': 'Health'
        }
    },
    'greet': {
        'takes': {
            'elements': {
                'name': {
                    'description': 'The name of the person to greet',
                    'tags': ['widget:textinput'],
                    'writeable': True,
                    'label': 'Name'
                },
                'sleep': {
                    'dtype': 'float64',
                    'description': 'Time to wait before returning',
                    'tags': ['widget:textinput'],
                    'writeable': True,
                    'label': 'Sleep'
                }
            },
            'required': ["name"]
        },
        'defaults': {
            'sleep': 0.0
        },
        'description': 'Optionally sleep <sleep> seconds, then return a greeting to <name>',
        'tags': ['method:return:unpacked'],
        'writeable': True,
        'label': 'Greet',
        'returns': {
            'elements': {
                'return': {
                    'description': 'The manufactured greeting',
                    'tags': ['widget:textupdate'],
                    'writeable': False,
                    'label': 'Return'
                }
            },
            'required': ['return']
        }
    },
    'error': {
        'takes': empty_map_meta_dict,
        'description': 'Raise an error',
        'tags': [],
        'writeable': True,
        'label': 'Error',
        'returns': empty_map_meta_dict
    }
}

hello_expected = Value(hello_block_t, hello_dict)


# These tests need a server running
class TestPVAServer(unittest.TestCase):
    SEQ = 0

    def setUp(self):
        TestPVAServer.SEQ += 1
        if not PVAPY:
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
        cothread = maybe_import_cothread()
        if cothread:
            from p4p.client.cothread import Context
        else:
            from p4p.client.thread import Context
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
            return len(split) > 1 and split[1] in ("secondsPastEpoch", "nanoseconds")

        for f, s in zip(firstlines, secondlines):
            if not same:
                break
            if not linejunk(s):
                same &= f == s
        if not same:
            diff = '\n' + ''.join(
                difflib.ndiff(firstlines, secondlines, linejunk))
            self.fail(diff)

    # Equivalent to:
    #   pvget TESTCOUNTER -r ""
    def testGetEverything(self):
        counter = self.ctxt.get("TESTCOUNTER")
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))
        self.assertEqual(counter.getID(), "malcolm:core/Block:1.0")
        names = list(counter)
        self.assertEqual(names,
                         ["meta", "health", "counter", "zero", "increment"])
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
        self.assertEqual(len(counter.meta.fields), 4)
        fields_code = dict(counter.meta.type().items())["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to:
    #   pvget TESTCOUNTER -r junk.thing
    def atestGetBadSubfield(self):
        if PVAPY:
            # Currently only returns an error structure as pvaPy can't raise
            # exceptions
            error = self.ctxt.get("TESTCOUNTER", "junk.thing")
            self.assertEqual(error.getID(), "malcolm:core/Error:1.0")
            self.assertEqual(error.message, "UnexpectedError: Object ['TESTCOUNTER'] of type 'malcolm:core/Block:1.0' has no attribute 'junk'")
        else:
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
        self.assertEqual(len(meta.fields), 4)
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
        if PVAPY:
            # Get it over pva
            counter = self.ctxt.get("TESTCOUNTER.counter").value
        else:
            # Get it directly from the data structure
            counter = self.counter.make_view().counter.value
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
        self.assertTrue(counter.changedSet().issuperset({
            "meta.fields", "counter.value", "zero.description"}))
        self.assertEqual(counter["counter.value"], 0)
        self.assertEqual(counter["zero.description"],
                         "Zero the counter attribute")
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q.get(timeout=1)
        self.assertEqual(counter.counter.value, 5)
        if PVAPY:
            # bitsets in pvaPy don't work, so it is everything at the moment
            self.assertTrue(counter.changedSet().issuperset({
                "meta", "meta.fields", "counter", "zero"}))
        else:
            self.assertEqual(counter.changedSet(),
                             {"counter.value",
                              "counter.timeStamp.userTag",
                              "counter.timeStamp.secondsPastEpoch",
                              "counter.timeStamp.nanoseconds"})
        self.ctxt.put("TESTCOUNTER.counter", 0, "value")
        counter = q.get(timeout=1)
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))

    def testTwoMonitors(self):
        if PVAPY:
            # No need to do this test on the old server
            return
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
        if PVAPY:
            # PVAPY says everything is changed
            self.assertEqual(counter.changedSet(), {"meta", "meta.fields"})
        else:
            # P4P only says leaves have changed
            self.assertEqual(counter.changedSet(), {"meta.fields"})
        self.assertEqual(counter.meta.fields,
                         ["health", "counter", "zero", "increment"])
        fields_code = dict(counter.meta.type().aspy()[2])["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to
    #   pvget -m TESTCOUNTER.counter -r ""
    def testMonitorDotted(self):
        q = Queue()
        m = self.ctxt.monitor("TESTCOUNTER.counter", q.put)
        self.addCleanup(m.close)
        counter = q.get(timeout=1)  # type: Value
        self.assertEqual(counter.getID(), "epics:nt/NTScalar:1.0")
        self.assertTrue(counter.changedSet().issuperset({
            "value", "alarm.severity", "timeStamp.userTag"}))
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q.get(timeout=1)
        self.assertEqual(counter.value, 5)
        if PVAPY:
            # bitsets in pvaPy don't work, so it is everything at the moment
            self.assertTrue(counter.changedSet().issuperset({
                "value", "alarm", "timeStamp"}))
        else:
            self.assertEqual(counter.changedSet(),
                             {"value",
                              "timeStamp.userTag",
                              "timeStamp.secondsPastEpoch",
                              "timeStamp.nanoseconds"})
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
        if PVAPY:
            # This doesn't raise on the pvaPy server as it cannot return errors
            error = self.ctxt.rpc("TESTHELLO.error", EMPTY)
            self.assertEqual(error.getID(), "malcolm:core/Error:1.0")
            self.assertEqual(error.message,
                             "RuntimeError: You called method error()")
        else:
            with self.assertRaises(RuntimeError) as cm:
                self.ctxt.rpc("TESTHELLO.error", EMPTY)
            self.assertEqual(str(cm.exception),
                             "RuntimeError: You called method error()")
