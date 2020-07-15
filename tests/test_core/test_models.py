import unittest
from collections import OrderedDict

import numpy as np
from annotypes import Serializable
from mock import Mock

from malcolm.core import (
    Alarm,
    AlarmSeverity,
    AlarmStatus,
    BlockModel,
    BooleanArrayMeta,
    BooleanMeta,
    ChoiceArrayMeta,
    ChoiceMeta,
    MethodModel,
    NumberArrayMeta,
    NumberMeta,
    StringArrayMeta,
    StringMeta,
    TableMeta,
    TimeStamp,
    VMeta,
)
from malcolm.core.models import (
    BlockMeta,
    MapMeta,
    Meta,
    MethodLog,
    MethodMeta,
    NTScalar,
)
from malcolm.core.notifier import DummyNotifier


class TestAttribute(unittest.TestCase):
    def setUp(self):
        self.meta = StringMeta()
        self.o = self.meta.create_attribute_model()

    def test_init(self):
        self.assertIs(self.o.meta, self.meta)
        assert self.o.value == ""
        assert self.o.typeid == "epics:nt/NTScalar:1.0"

    def test_set_value(self):
        value = "test_value"
        self.o.set_value(value)
        assert self.o.value == value

    def test_set_alarm(self):
        alarm = Alarm(AlarmSeverity.MAJOR_ALARM, AlarmStatus.DEVICE_STATUS, "bad")
        self.o.set_alarm(alarm)
        assert self.o.alarm == alarm

    def test_set_timeStamp(self):
        timeStamp = TimeStamp()
        self.o.set_timeStamp(timeStamp)
        assert self.o.timeStamp == timeStamp


class TestNTScalar(unittest.TestCase):
    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "epics:nt/NTScalar:1.0"
        self.serialized["value"] = "some string"
        self.serialized["alarm"] = Alarm().to_dict()
        self.serialized["timeStamp"] = TimeStamp().to_dict()
        self.serialized["meta"] = StringMeta("desc").to_dict()

    def test_to_dict(self):
        a = StringMeta("desc").create_attribute_model()
        a.set_value("some string")
        a.set_timeStamp(self.serialized["timeStamp"])
        assert a.to_dict() == self.serialized

    def test_from_dict(self):
        a = NTScalar.from_dict(self.serialized)
        assert a.meta.to_dict() == StringMeta("desc").to_dict()
        assert a.value == "some string"


class TestBlockMeta(unittest.TestCase):
    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/BlockMeta:1.0"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = True
        self.serialized["label"] = ""
        self.serialized["fields"] = []

    def test_to_dict(self):
        m = BlockMeta("desc")
        assert m.to_dict() == self.serialized

    def test_from_dict(self):
        m = BlockMeta.from_dict(self.serialized)
        assert m.description == "desc"
        assert m.tags == []
        assert m.writeable is True
        assert m.label == ""


class TestBlockModel(unittest.TestCase):
    def setUp(self):
        self.attr = StringMeta().create_attribute_model()
        self.method = MethodModel()
        self.o = BlockModel()
        self.o.set_endpoint_data("attr", self.attr)
        self.o.set_endpoint_data("method", self.method)

    def test_init(self):
        assert self.o.method == self.method
        assert self.o.attr == self.attr
        assert self.o.typeid == "malcolm:core/Block:1.0"
        assert list(self.o) == ["meta", "attr", "method"]

    def test_remove_endpoint(self):
        self.o.remove_endpoint("attr")
        assert self.o.method == self.method
        assert list(self.o) == ["meta", "method"]
        assert self.o.meta.fields == ["method"]
        with self.assertRaises(AttributeError):
            self.o.attr
        self.o.set_endpoint_data("attr", self.attr)
        assert list(self.o) == ["meta", "method", "attr"]
        assert self.o.meta.fields == ["method", "attr"]
        assert self.o.attr == self.attr


class TestBooleanArrayMeta(unittest.TestCase):
    def setUp(self):
        self.meta = BooleanArrayMeta("test description")

    def test_init(self):
        assert "test description" == self.meta.description
        assert self.meta.label == ""
        assert self.meta.typeid == "malcolm:core/BooleanArrayMeta:1.0"

    def test_validate_none(self):
        assert list(self.meta.validate(None)) == []

    def test_validate_array(self):
        array = ["True", "", True, False, 1, 0]
        assert ([True, False, True, False, True, False]) == (
            list(self.meta.validate(array))
        )

    def test_not_iterable(self):
        value = True
        assert self.meta.validate(value) == [True]

    def test_null_element_raises(self):
        array = ["test", None]
        assert ([True, False]) == list(self.meta.validate(array))


class TestBooleanMeta(unittest.TestCase):
    def setUp(self):
        self.boolean_meta = BooleanMeta("test description")

    def test_given_value_str_then_cast_and_return(self):
        response = self.boolean_meta.validate("TestValue")
        assert response

        response = self.boolean_meta.validate("")
        assert not response

    def test_given_value_int_then_cast_and_return(self):
        response = self.boolean_meta.validate(15)
        assert response

        response = self.boolean_meta.validate(0)
        assert not response

    def test_given_value_boolean_then_cast_and_return(self):
        response = self.boolean_meta.validate(True)
        assert response

        response = self.boolean_meta.validate(False)
        assert not response

    def test_given_value_None_then_return(self):
        response = self.boolean_meta.validate(None)

        assert False is response


class TestChoiceArrayMeta(unittest.TestCase):
    def setUp(self):
        self.meta = ChoiceArrayMeta("test description", ["a", "b"])

    def test_init(self):
        self.meta = ChoiceArrayMeta("test description", ["a", "b"])
        assert "test description" == self.meta.description
        assert self.meta.label == ""
        assert self.meta.typeid == "malcolm:core/ChoiceArrayMeta:1.0"
        assert self.meta.choices == ["a", "b"]

    def test_validate_none(self):
        assert self.meta.validate(None) == []

    def test_validate(self):
        response = self.meta.validate(["b", "a"])
        assert ["b", "a"] == response

    def test_not_iterable_raises(self):
        value = "abb"
        with self.assertRaises(ValueError):
            self.meta.validate(value)

    def test_null_element_maps_default(self):
        array = ["b", None]
        assert self.meta.validate(array) == ["b", "a"]

    def test_invalid_choice_raises(self):
        with self.assertRaises(ValueError):
            self.meta.validate(["a", "x"])


class TestChoiceMeta(unittest.TestCase):
    def setUp(self):
        self.choice_meta = ChoiceMeta("test description", ["a", "b"])
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/ChoiceMeta:1.0"
        self.serialized["description"] = "desc"
        self.serialized["choices"] = ["a", "b"]
        self.serialized["tags"] = []
        self.serialized["writeable"] = False
        self.serialized["label"] = "name"

    def test_init(self):
        self.choice_meta = ChoiceMeta("test description", ["a", "b"])
        assert ("test description") == self.choice_meta.description
        assert (self.choice_meta.typeid) == "malcolm:core/ChoiceMeta:1.0"
        assert (self.choice_meta.label) == ""
        assert (self.choice_meta.choices) == ["a", "b"]

    def test_given_valid_value_then_return(self):
        response = self.choice_meta.validate("a")
        assert "a" == response

    def test_int_validate(self):
        response = self.choice_meta.validate(1)
        assert "b" == response

    def test_None_valid(self):
        response = self.choice_meta.validate(None)
        assert "a" == response

    def test_given_invalid_value_then_raises(self):
        with self.assertRaises(ValueError):
            self.choice_meta.validate("badname")

    def test_set_choices(self):
        self.choice_meta.set_choices(["4"])

        assert ["4"] == self.choice_meta.choices

    def test_to_dict(self):
        bm = ChoiceMeta("desc", ["a", "b"], label="name")
        assert bm.to_dict() == self.serialized

    def test_from_dict(self):
        bm = ChoiceMeta.from_dict(self.serialized)
        assert type(bm) == ChoiceMeta
        assert bm.description == "desc"
        assert bm.choices == ["a", "b"]
        assert bm.tags == []
        assert not bm.writeable
        assert bm.label == "name"


class TestMethodMeta(unittest.TestCase):
    def test_init(self):
        m = MethodMeta(description="test_description")
        assert "test_description" == m.description
        assert "malcolm:core/MethodMeta:1.1" == m.typeid
        assert "" == m.label

    def test_set_label(self):
        m = MethodMeta(description="test_description")
        m.set_label("new_label")
        assert "new_label" == m.label

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/MethodMeta:1.1"
        self.takes = MapMeta()
        self.takes.set_elements({"in_attr": StringMeta("desc")})
        self.serialized["takes"] = self.takes.to_dict()
        self.serialized["defaults"] = OrderedDict({"in_attr": "default"})
        self.serialized["description"] = "test_description"
        self.serialized["tags"] = []
        self.serialized["writeable"] = False
        self.serialized["label"] = ""
        self.serialized["returns"] = MapMeta().to_dict()

    def test_to_dict(self):
        m = MethodMeta(description="test_description")
        m.set_takes(self.takes)
        m.set_defaults(self.serialized["defaults"])
        assert m.to_dict() == self.serialized

    def test_from_dict(self):
        m = MethodMeta.from_dict(self.serialized)
        assert m.takes.to_dict() == self.takes.to_dict()
        assert m.defaults == self.serialized["defaults"]
        assert m.tags == []
        assert m.writeable is False
        assert m.label == ""
        assert m.returns.to_dict() == MapMeta().to_dict()


class TestMethodLog(unittest.TestCase):
    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/MethodLog:1.0"
        self.serialized["value"] = dict(a=1)
        self.serialized["present"] = ["a"]
        self.serialized["alarm"] = Alarm.ok.to_dict()
        self.serialized["timeStamp"] = TimeStamp.zero.to_dict()

    def test_to_dict(self):
        m = MethodLog(value=dict(a=1), present=["a"], timeStamp=TimeStamp.zero)
        assert m.to_dict() == self.serialized

    def test_from_dict(self):
        m = MethodLog.from_dict(self.serialized)
        assert m.value == dict(a=1)
        assert m.present == ["a"]
        assert m.alarm.to_dict() == Alarm.ok.to_dict()
        assert m.timeStamp.to_dict() == TimeStamp.zero.to_dict()


class TestMapMeta(unittest.TestCase):
    def test_values_set(self):
        self.assertIsInstance(self.mm.elements, dict)
        assert len(self.mm.elements) == 0
        assert self.mm.typeid == "malcolm:core/MapMeta:1.0"

    def test_set_elements(self):
        els = dict(sam=StringArrayMeta())
        self.mm.set_elements(els)
        assert self.mm.elements == els

    def test_set_required(self):
        self.test_set_elements()
        req = ("sam",)
        self.mm.set_required(req)
        assert self.mm.required == req

    def setUp(self):
        self.mm = MapMeta()
        self.sam = StringArrayMeta()
        self.sam.label = "C1"
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/MapMeta:1.0"
        self.serialized["elements"] = dict(c1=self.sam.to_dict())
        self.serialized["required"] = ["c1"]

    def test_to_dict(self):
        tm = MapMeta()
        tm.set_elements(dict(c1=self.sam))
        tm.set_required(["c1"])
        assert tm.to_dict() == self.serialized

    def test_from_dict(self):
        tm = MapMeta.from_dict(self.serialized)
        assert len(tm.elements) == 1
        expected = self.sam.to_dict()
        assert tm.elements["c1"].to_dict() == expected


class TestMeta(unittest.TestCase):
    def setUp(self):
        self.o = Meta("desc")
        notifier = DummyNotifier()
        notifier.add_squashed_change = Mock()
        self.o.set_notifier_path(notifier, ["path"])
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "filled_in_by_subclass"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = False
        self.serialized["label"] = ""

    def test_set_description(self):
        description = "desc2"
        assert self.o.set_description(description) == description
        assert self.o.description == description
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "description"], description
        )

    def test_set_tags(self):
        tags = ("widget:textinput",)
        assert self.o.set_tags(tags) == tags
        assert self.o.tags == tags
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "tags"], tags
        )

    def test_set_writeable(self):
        writeable = True
        assert self.o.set_writeable(writeable) == writeable
        assert self.o.writeable == writeable
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "writeable"], writeable
        )

    def test_set_label(self):
        label = "my label"
        assert self.o.set_label(label) == label
        assert self.o.label == label
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "label"], label
        )

    def test_to_dict(self):
        m = Meta("desc")
        m.typeid = "filled_in_by_subclass"
        assert m.to_dict() == self.serialized


class TestNumberArrayMeta(unittest.TestCase):
    def test_numpy_array(self):
        nm = NumberArrayMeta("float64")
        values = np.array([1.2, 3.4, 5.6])
        response = nm.validate(values)

        for i, value in enumerate(response):
            assert values[i] == value

    def test_numpy_array_wrong_type_raises(self):
        nm = NumberArrayMeta("float64")
        values = "[1.2, 3.4, 5.6]"

        with self.assertRaises(ValueError):
            nm.validate(values)

    def test_numpy_array_wrong_number_type_raises(self):
        nm = NumberArrayMeta("int32")
        values = np.array([1.2, 3.4, 5.6])

        with self.assertRaises(AssertionError):
            nm.validate(values)

    def test_float_against_float64(self):
        nm = NumberArrayMeta("float64")
        values = [1.2, 3.4, 5.6]
        response = nm.validate(values)

        for i, value in enumerate(response):
            assert values[i] == value

    def test_float_against_float32(self):
        nm = NumberArrayMeta("float32")
        values = [1.2, 3.4, 5.6]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertAlmostEqual(values[i], response[i], places=5)

    def test_int_against_float(self):
        nm = NumberArrayMeta("float32")
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            assert values[i] == value

        nm = NumberArrayMeta("float64")
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            assert values[i] == value

    def test_int_against_int(self):
        nm = NumberArrayMeta("int32")
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            assert values[i] == value

    def test_float_against_int_floors(self):
        nm = NumberArrayMeta("int32")
        actual = list(nm.validate([1.2, 34, 56]))
        expected = [1, 34, 56]
        assert actual == expected

    def test_null_element_zero(self):
        nm = NumberArrayMeta("float64")
        actual = nm.validate([1.2, None, 1.3])
        assert actual[0] == 1.2
        assert np.isnan(actual[1])
        assert actual[2] == 1.3

    def test_none_validates(self):
        nm = NumberArrayMeta("int32")
        assert list(nm.validate(None)) == []


class TestNumberMeta(unittest.TestCase):
    def test_init(self):
        nm = NumberMeta("float32")
        assert nm.typeid == "malcolm:core/NumberMeta:1.0"
        assert nm.dtype == "float32"
        assert nm.label == ""

    def test_float_against_float32(self):
        nm = NumberMeta("float32")
        self.assertAlmostEqual(123.456, nm.validate(123.456), places=5)

    def test_float_against_float64(self):
        nm = NumberMeta("float64")
        assert 123.456 == nm.validate(123.456)

    def test_int_against_float(self):
        nm = NumberMeta("float64")
        assert 123 == nm.validate(123)

    def test_int_against_int(self):
        nm = NumberMeta("int32")
        assert 123 == nm.validate(123)

    def test_float_to_int_truncates(self):
        nm = NumberMeta("int32")
        assert nm.validate(123.6) == 123

    def test_none_validates(self):
        nm = NumberMeta("int32")
        assert 0 == nm.validate(None)

    def test_unsigned_validates(self):
        nm = NumberMeta("uint32")
        assert nm.validate("22") == 22
        assert nm.validate(-22) == 2 ** 32 - 22

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/NumberMeta:1.0"
        self.serialized["dtype"] = "float64"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = False
        self.serialized["label"] = "name"
        display = OrderedDict()
        display["typeid"] = "display_t"
        display["limitLow"] = 0
        display["limitHigh"] = 0
        display["description"] = ""
        display["precision"] = 8
        display["units"] = ""
        self.serialized["display"] = display

    def test_to_dict(self):
        nm = NumberMeta("float64", "desc", label="name")
        assert nm.to_dict() == self.serialized

    def test_from_dict(self):
        nm = NumberMeta.from_dict(self.serialized)
        assert type(nm) == NumberMeta
        assert nm.description == "desc"
        assert nm.dtype == "float64"
        assert nm.tags == []
        assert not nm.writeable
        assert nm.label == "name"


class TestStringArrayMeta(unittest.TestCase):
    def setUp(self):
        self.meta = StringArrayMeta("test description")

    def test_init(self):
        assert "test description" == self.meta.description
        assert self.meta.label == ""
        assert self.meta.typeid == "malcolm:core/StringArrayMeta:1.0"

    def test_validate_none(self):
        assert self.meta.validate(None) == []

    def test_validate_array(self):
        array = ["test_string", 123, 123.456]
        with self.assertRaises(AssertionError):
            self.meta.validate(array)

    def test_not_iterable_raises(self):
        value = 12346
        with self.assertRaises(AssertionError):
            self.meta.validate(value)

    def test_null_element_raises(self):
        array = ["test", None]
        with self.assertRaises(AssertionError):
            self.meta.validate(array)


class TestStringMeta(unittest.TestCase):
    def setUp(self):
        self.string_meta = StringMeta("test string description")

    def test_given_value_str_then_return(self):
        response = self.string_meta.validate("TestValue")

        assert "TestValue" == response

    def test_given_value_int_then_cast_and_return(self):
        response = self.string_meta.validate(15)

        assert "15" == response

    def test_given_value_float_then_cast_and_return(self):
        response = self.string_meta.validate(12.8)

        assert "12.8" == response

    def test_given_value_None_then_return(self):
        response = self.string_meta.validate(None)

        assert "" == response


class TestTableMeta(unittest.TestCase):
    def test_init(self):
        tm = TableMeta("desc")
        assert "desc" == tm.description
        assert "malcolm:core/TableMeta:1.0" == tm.typeid
        assert [] == tm.tags
        assert False is tm.writeable
        assert "" == tm.label

    def setUp(self):
        tm = TableMeta("desc")
        self.tm = tm
        self.tm.set_elements(dict(c1=StringArrayMeta()))
        self.sam = StringArrayMeta()
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/TableMeta:1.0"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = True
        self.serialized["label"] = "Name"
        self.serialized["elements"] = dict(c1=self.sam.to_dict())

    def test_set_elements(self):
        tm = self.tm
        elements = OrderedDict()
        elements["col1"] = StringArrayMeta()
        elements["col2"] = StringArrayMeta()
        tm.set_elements(elements)
        assert elements == tm.elements

    def test_set_elements_from_serialized(self):
        tm = self.tm
        elements = OrderedDict()
        elements["col1"] = StringArrayMeta().to_dict()
        elements["col2"] = StringArrayMeta().to_dict()
        tm.set_elements(elements)
        assert isinstance(tm.elements["col1"], StringArrayMeta)
        assert tm.elements["col1"].to_dict() == elements["col1"]

    def test_to_dict(self):
        tm = TableMeta("desc")
        tm.set_label("Name")
        tm.set_writeable(True)
        tm.set_elements(dict(c1=self.sam))
        assert tm.to_dict() == self.serialized

    def test_from_dict(self):
        tm = TableMeta.from_dict(self.serialized)
        assert tm.description == "desc"
        assert len(tm.elements) == 1
        assert tm.elements["c1"].to_dict() == self.sam.to_dict()
        assert tm.tags == []
        assert tm.writeable is True
        assert tm.label == "Name"

    def test_validate_from_good_table(self):
        tm = self.tm
        t = tm.table_cls(c1=["me", "me3"])
        t_serialized = t.to_dict()
        t = tm.validate(t)
        assert t.to_dict() == t_serialized

    def test_validate_from_serialized(self):
        tm = self.tm
        serialized = dict(typeid="anything", c1=("me", "me3"))
        t = tm.validate(serialized)
        assert list(t) == ["c1"]
        assert t.c1 == serialized["c1"]


class TestVMeta(unittest.TestCase):
    def test_values_after_init(self):
        assert "test description" == self.meta.description
        assert not self.meta.writeable

    def test_given_validate_called_then_raise_error(self):
        with self.assertRaises(NotImplementedError):
            self.meta.validate(1)

    def setUp(self):
        self.meta = VMeta("test description")
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "filled_in_by_subclass"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = True
        self.serialized["label"] = "my label"

    def test_to_dict(self):
        m = VMeta("desc", writeable=True, label="my label")
        m.typeid = "filled_in_by_subclass"
        assert m.to_dict() == self.serialized

    def test_from_dict(self):
        @Serializable.register_subclass("filled_in_by_subclass")
        class MyVMeta(VMeta):
            pass

        m = MyVMeta.from_dict(self.serialized)
        assert m.description == "desc"
        assert m.tags == []
        assert m.writeable is True
        assert m.label == "my label"
