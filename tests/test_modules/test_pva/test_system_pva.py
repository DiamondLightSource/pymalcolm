from __future__ import print_function

import difflib
import unittest

from p4p.nt.scalar import ntfloat
# TODO: TimeoutError is not in __all__, is this the right import?
from p4p.client.thread import TimeoutError
from p4p import Value, Type

from malcolm.compat import maybe_import_cothread
from malcolm.core import Process, Queue
from malcolm.modules.demo.blocks import hello_block, counter_block
from malcolm.modules.pva.blocks import pva_server_block
from malcolm.modules.pva.controllers.pvaconvert import \
    convert_dict_to_value, NOTHING


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
class SystemClientServer(unittest.TestCase):

    def setUp(self):
        if not PVAPY:
            self.process = Process("proc")
            self.hello = hello_block(mri="TESTHELLO")[-1]
            self.process.add_controller(self.hello)
            self.counter = counter_block(mri="TESTCOUNTER")[-1]
            self.process.add_controller(self.counter)
            self.server = pva_server_block(mri="PVA")[-1]
            self.process.add_controller(self.server)
            self.process.start()
            self.addCleanup(self.process.stop, timeout=2)
        self.ctxt = self.make_pva_context(unwrap=False)
        self.addCleanup(self.ctxt.close)

    def make_pva_context(self, *args, **kwargs):
        cothread = maybe_import_cothread()
        if cothread:
            raise RuntimeError("Can't do this until we have cothread Context")
        else:
            from p4p.client.thread import Context
        return Context("pva", *args, **kwargs)

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
        # TODO: Value.__iter__ would let us do:
        #   names = list(counter)
        names = [k for k, v in counter.items()]
        self.assertEqual(names,
                         ["meta", "health", "counter", "zero", "increment"])
        self.assertEqual(counter.meta.getID(), "malcolm:core/BlockMeta:1.0")
        self.assertEqual(counter.meta.label, "TESTCOUNTER")
        self.assertEqual(counter.meta.fields, names[1:])
        mtype = counter.meta.type()
        # TODO: Type.type_codes() would let us do
        #   fields_code = mtype.type_codes()["fields"]
        fields_code = dict(mtype.aspy()[2])["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to:
    #   pvget TESTHELLO -r ""
    def testGetEverythingHello(self):
        hello = self.ctxt.get("TESTHELLO")
        self.assertStructureWithoutTsEqual(str(hello), str(hello_expected))

    # Equivalent to:
    #   pvget TESTCOUNTER -r meta.fields
    def testGetSubfield(self):
        request = convert_dict_to_value(dict(meta=dict(fields={})))
        counter = self.ctxt.get("TESTCOUNTER", request)
        self.assertEqual(counter.getID(), "structure")
        self.assertEqual(len(counter.items()), 1)
        self.assertEqual(len(counter.meta.items()), 1)
        self.assertEqual(len(counter.meta.fields), 4)
        fields_code = dict(counter.meta.type().aspy()[2])["fields"]
        self.assertEqual(fields_code, "as")

    # Equivalent to:
    #   pvget TESTCOUNTER -r junk.thing
    def testGetBadSubfield(self):
        request = convert_dict_to_value(dict(junk=dict(thing={})))
        if PVAPY:
            # Currently only returns an error structure as pvaPy can't raise
            # exceptions
            error = self.ctxt.get("TESTCOUNTER", request)
            self.assertEqual(error.getID(), "malcolm:core/Error:1.0")
            self.assertEqual(error.message, "UnexpectedError: Object ['TESTCOUNTER'] of type 'malcolm:core/Block:1.0' has no attribute 'junk'")
        else:
            # TODO: What is the right error to get here?
            with self.assertRaises(KeyError):
                self.ctxt.get("TESTCOUNTER", request)

    # Equivalent to:
    #   pvget BADCHANNEL -r ""
    def testGetBadChannel(self):
        with self.assertRaises(TimeoutError):
            self.ctxt.get("BADCHANNEL", timeout=1.0)

    # Equivalent to:
    #   pvget TESTCOUNTER.meta -r fields
    def testGetDottedSubfield(self):
        request = convert_dict_to_value(dict(fields={}))
        meta = self.ctxt.get("TESTCOUNTER.meta", request)
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
        self.addCleanup(ctxt.close)
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
        counter = self.ctxt.get("TESTCOUNTER.counter").value
        self.assertEqual(counter, value)

    # Should be equivalent to (except pvput doesn't do the right thing):
    #   pvput TESTCOUNTER -r "counter.value" 5
    def testPut(self):
        request = convert_dict_to_value(dict(counter=dict(value={})))
        self.assertCounter(0)
        self.ctxt.put("TESTCOUNTER", 5, request)
        self.assertCounter(5)
        self.ctxt.put("TESTCOUNTER", 0, request)
        self.assertCounter(0)

    # Equivalent to:
    #   pvput TESTCOUNTER.counter 5
    def testPutDotted(self):
        self.assertCounter(0)
        # TODO: pvput defaults the request to "value", should p4p do the same?
        self.ctxt.put("TESTCOUNTER.counter", 5, convert_dict_to_value(dict(value={})))
        self.assertCounter(5)
        self.ctxt.put("TESTCOUNTER.counter", dict(value=0))
        self.assertCounter(0)

    # Equivalent to:
    #   pvget -m TESTCOUNTER -r ""
    def testMonitorEverythingInitial(self):
        q = Queue()
        m = self.ctxt.monitor("TESTCOUNTER", q.put)
        self.addCleanup(m.close)
        counter = q.get()
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))
        self.assertTrue(counter.asSet().issuperset({
            "meta", "meta.fields", "counter", "zero"}))
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q.get()
        self.assertEqual(counter.counter.value, 5)
        if PVAPY:
            # bitsets in pvaPy don't work, so it is everything at the moment
            self.assertTrue(counter.asSet().issuperset({
                "meta", "meta.fields", "counter", "zero"}))
        else:
            # TODO: timeStamp userTag didn't change value, but timeStamp did,
            # should it be in the bitset?
            self.assertEqual(counter.asSet(),
                             {"counter.value", "counter.timeStamp",
                              "counter.timeStamp.secondsPastEpoch"
                              "counter.timeStamp.nanoseconds"})
        self.ctxt.put("TESTCOUNTER.counter", 0, "value")
        counter = q.get()
        # TODO: Is this true even if you get a subset of changes?
        self.assertStructureWithoutTsEqual(str(counter), str(counter_expected))

    # Equivalent to:
    #   pvget -m TESTCOUNTER -r meta.fields
    def testMonitorSubfieldInitial(self):
        q = Queue()
        request = convert_dict_to_value(dict(meta=dict(fields={})))
        m = self.ctxt.monitor("TESTCOUNTER", q.put, request)
        self.addCleanup(m.close)
        counter = q.get()
        self.assertEqual(counter.getID(), "structure")
        self.assertEqual(counter.asSet(), {"meta", "meta.fields"})
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
        counter = q.get()
        self.assertEqual(counter.getID(), "epics:nt/NTScalar:1.0")
        self.assertTrue(counter.asSet().issuperset({
            "value", "alarm", "timeStamp"}))
        self.ctxt.put("TESTCOUNTER.counter", 5, "value")
        counter = q.get()
        self.assertEqual(counter.value, 5)
        if PVAPY:
            # bitsets in pvaPy don't work, so it is everything at the moment
            self.assertTrue(counter.asSet().issuperset({
                "value", "alarm", "timeStamp"}))
        else:
            # TODO: timeStamp userTag didn't change value, but timeStamp did,
            # should it be in the bitset?
            self.assertEqual(counter.asSet(),
                             {"value", "timeStamp",
                              "timeStamp.secondsPastEpoch"
                              "timeStamp.nanoseconds"})
        self.ctxt.put("TESTCOUNTER.counter", 0, "value")
        counter = q.get()
        self.assertEqual(counter.value, 0)

    def testRpcRoot(self):
        method = Value(Type([("method", "s")]), dict(method="zero"))
        self.ctxt.rpc("TESTCOUNTER", NOTHING, method)
        self.assertCounter(0)
        # TODO: Would be friendly to allow value=None to send empty structure
        method = Value(Type([("method", "s")]), dict(method="increment"))
        ret = self.ctxt.rpc("TESTCOUNTER", NOTHING, method)
        self.assertEqual(ret.tolist(), [])
        self.assertCounter(1)
        method = Value(Type([("method", "s")]), dict(method="zero"))
        self.ctxt.rpc("TESTCOUNTER", NOTHING, method)
        self.assertCounter(0)

    def testRpcDotted(self):
        self.ctxt.rpc("TESTCOUNTER.zero", NOTHING)
        self.assertCounter(0)
        result = self.ctxt.rpc("TESTCOUNTER.increment", NOTHING)
        self.assertEqual(dict(result.items()), {})
        self.assertCounter(1)
        self.ctxt.rpc("TESTCOUNTER.zero", NOTHING)
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

    def testRpcError(self):
        if PVAPY:
            # This doesn't raise on the pvaPy server as it cannot return errors
            error = self.ctxt.rpc("TESTHELLO.error", NOTHING)
            self.assertEqual(error.getID(), "malcolm:core/Error:1.0")
            self.assertEqual(error.message,
                             "RuntimeError: You called method error()")
        else:
            with self.assertRaises(RuntimeError) as cm:
                self.ctxt.rpc("TESTHELLO.error", NOTHING)
            self.assertEqual(str(cm.exception), "RuntimeError: You called method error()")

