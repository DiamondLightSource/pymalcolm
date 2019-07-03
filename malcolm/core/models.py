import inspect

from annotypes import Array, Anno, Union, Sequence, Mapping, Any, to_array, \
    Optional, TYPE_CHECKING, WithCallTypes, NO_DEFAULT, Serializable, \
    deserialize_object, FrozenOrderedDict

import numpy as np
from enum import Enum

from malcolm.compat import OrderedDict, str_
from .alarm import Alarm
from .notifier import DummyNotifier, Notifier
from .camel import camel_to_title
from .table import Table
from .tags import Widget, method_return_unpacked
from .timestamp import TimeStamp

if TYPE_CHECKING:
    from typing import Tuple, Type, List, Dict, Callable


def check_type(value, typ):
    if typ != Any:
        if typ == str:
            typ = str_
        assert isinstance(value, typ), "Expected %s, got %r" % (typ, value)


class Model(Serializable):
    notifier = DummyNotifier()
    path = []
    __slots__ = []

    def set_notifier_path(self, notifier, path):
        """Sets the notifier, and the path from the path from block root

        Args:
            notifier (Notifier): The Notifier to tell when endpoint data changes
            path (list): The absolute path to get to this object
        """
        # type: (Union[Notifier, DummyNotifier], List[str]) -> None
        # This function should either change from the DummyNotifier or to
        # the DummyNotifier, never between two valid notifiers
        assert self.notifier is Model.notifier or notifier is Model.notifier, \
            "Already have a notifier %s path %s" % (self.notifier, self.path)
        self.notifier = notifier
        self.path = path
        # Tell all our children too
        for name, ct in self.call_types.items():
            if ct.is_mapping:
                child = getattr(self, name)
                if child and Model.matches_type(ct.typ[1]):
                    for k, v in child.items():
                        v.set_notifier_path(notifier, self.path + [name, k])
            elif Model.matches_type(ct.typ):
                assert not ct.is_array, \
                    "Can't deal with Arrays of Models %s" % ct
                child = getattr(self, name)
                child.set_notifier_path(notifier, self.path + [name])

    def set_endpoint_data(self, name, value):
        # type: (str_, Any) -> Any
        try:
            ct = self.call_types[name]
        except KeyError:
            raise ValueError("%r not in %r.call_types %r" % (
                name, self, self.call_types))
        else:
            if ct.is_array:
                # Cast to right type, this will do some cheap validation
                value = ct(value)  # type: Array
                # Check we have the right type
                assert not Model.matches_type(ct.typ), \
                    "Can't handle Array[Model] at the moment"
                if isinstance(value.seq, (tuple, list)):
                    # Variable array, check types of each instance
                    # TODO: this might harm performance
                    if ct.typ == str:
                        typ = str_
                    else:
                        typ = ct.typ
                    for x in value.seq:
                        assert isinstance(x, typ), \
                            "Expected Array[%r], got %r" % (ct.typ, value.seq)
            elif ct.is_mapping:
                # Check it is the right type
                ktype, vtype = ct.typ
                for k, v in value.items():
                    check_type(k, ktype)
                    check_type(v, vtype)
                # If we are setting structures of Models then sort notification
                if Model.matches_type(ct.typ[1]):
                    # If we have old Models then stop them notifying
                    child = getattr(self, name, {})
                    if child:
                        for k, v in child.items():
                            v.set_notifier_path(Model.notifier, [])
                    for k, v in value.items():
                        v.set_notifier_path(self.notifier,
                                            self.path + [name, k])
            else:
                # If we are setting a Model then sort notification
                if Model.matches_type(ct.typ):
                    # If we have an old Model then stop it notifying
                    child = getattr(self, name, None)
                    if child:
                        child.set_notifier_path(Model.notifier, [])
                    value.set_notifier_path(self.notifier, self.path + [name])
                # Make sure it is the right typ
                check_type(value, ct.typ)
            with self.notifier.changes_squashed:
                # Actually set the attribute
                setattr(self, name, value)
                # Tell the notifier what changed
                self.notifier.add_squashed_change(self.path + [name], value)
            return value

    def apply_change(self, path, *args):
        # type: (List[str], Any) -> None
        """Take a single change from a Delta and apply it to this model"""
        if len(path) > 1:
            # This is for a child
            self[path[0]].apply_change(path[1:], *args)
        else:
            # This is for us
            assert len(path) == 1 and len(args) == 1, \
                "Cannot process change %s" % ([self.path + path] + list(args))
            getattr(self, "set_%s" % path[0])(args[0])


# Types used when deserializing to the class
with Anno("Description of what this element represents"):
    AMetaDescription = str
with Anno("Generic text tags for client tools to interpret"):
    ATags = Array[str]
with Anno("Whether this element is currently writeable"):
    AWriteable = bool
with Anno("A human readable label for the element"):
    ALabel = str

# A more permissive union to allow a wider range of set_* args
UTags = Union[ATags, Sequence[str], str]


class Meta(Model):
    """Base class for describing Blocks, Methods and Attributes"""
    __slots__ = ["description", "tags", "writeable", "label"]

    def __init__(self, description="", tags=(), writeable=False, label=""):
        # type: (AMetaDescription, UTags, AWriteable, ALabel) -> None
        self.description = self.set_description(description)
        self.tags = self.set_tags(tags)
        self.writeable = self.set_writeable(writeable)
        self.label = self.set_label(label)

    def set_description(self, description):
        # type: (AMetaDescription) -> AMetaDescription
        return self.set_endpoint_data("description", description)

    def set_tags(self, tags):
        # type: (UTags) -> ATags
        return self.set_endpoint_data("tags", tags)

    def set_writeable(self, writeable):
        # type: (AWriteable) -> AWriteable
        return self.set_endpoint_data("writeable", writeable)

    def set_label(self, label):
        # type: (ALabel) -> ALabel
        return self.set_endpoint_data("label", label)


class VMeta(Meta):
    """Abstract base class for validating the values of Attributes"""
    attribute_class = None
    _annotype_lookup = {}  # type: Mapping[Tuple[type, bool, bool], Type[VMeta]]
    __slots__ = []

    def validate(self, value):
        # type: (Any) ->  Any
        """Abstract function to validate a given value

        Args:
            value: Value to validate

        Returns:
            The validated value if it passes
        """
        raise NotImplementedError(self)

    def create_attribute_model(self, initial_value=None):
        # type: (Any) -> AttributeModel
        """Make an AttributeModel instance of the correct type for this Meta

        Args:
            initial_value: The initial value the Attribute should take

        Returns:
            AttributeModel: The created attribute model instance
        """
        attr = self.attribute_class(meta=self, value=initial_value)
        return attr

    def doc_type_string(self):
        # type: () -> str
        """Abstract function to return the python type string.

        For example, "str" or "numpy.int32"
        """
        raise NotImplementedError(self)

    def default_widget(self):
        # type: () -> Widget
        """Abstract function to return the default widget type"""
        raise NotImplementedError(self)

    @classmethod
    def from_annotype(cls, anno, writeable, **kwargs):
        # type: (Anno, bool, **Any) -> VMeta
        """Return an instance of this class from an Anno"""
        ret = cls(description=anno.description, writeable=writeable, **kwargs)
        widget = ret.default_widget()
        if widget != Widget.NONE:
            ret.set_tags([widget.tag()])
        return ret

    @classmethod
    def register_annotype_converter(cls, types, is_array=False,
                                    is_mapping=False):
        # type: (Union[Sequence[type], type], bool, bool) -> Any
        """Register this class as a converter for Anno instances"""
        if not isinstance(types, Sequence):
            types = [types]

        def decorator(subclass):
            for typ in types:
                cls._annotype_lookup[(typ, is_array, is_mapping)] = subclass
            return subclass

        return decorator

    @classmethod
    def lookup_annotype_converter(cls, anno):
        # type: (Anno) -> Type[VMeta]
        """Look up a vmeta based on an Anno"""
        if hasattr(anno.typ, "__bases__"):
            # This is a proper type
            bases = inspect.getmro(anno.typ)
        else:
            # This is a numpy dtype
            bases = [anno.typ]
        for typ in bases:
            key = (typ, bool(anno.is_array), bool(anno.is_mapping))
            try:
                return cls._annotype_lookup[key]
            except KeyError:
                pass
        raise KeyError(anno)


# Types used when deserializing to the class
with Anno("The current value of the Attribute"):
    AValue = Any
with Anno("The current alarm status"):
    AAlarm = Alarm
with Anno("The time when the value was last updated"):
    ATimeStamp = TimeStamp
with Anno("The validating Meta object describing our value"):
    AVMeta = VMeta


# Don't register this with Serializable as we never instantiate it directly,
# only a subclass like NTScalar
class AttributeModel(Model):
    """Data Model for an Attribute"""
    __slots__ = ["value", "alarm", "timeStamp", "meta"]

    # noinspection PyPep8Naming
    # timeStamp is camelCase to maintain compatibility with EPICS normative
    # types
    def __init__(self, value=None, alarm=None, timeStamp=None, meta=None):
        # type: (AValue, AAlarm, ATimeStamp, AVMeta) -> None
        self.meta = self.set_meta(meta)
        """A Meta object describing the Attribute"""
        self.value = self.set_value(value, set_alarm_ts=False)
        """The current value of the Attribute"""
        self.alarm = self.set_alarm(alarm)
        """An Alarm object indicating any problems"""
        self.timeStamp = self.set_timeStamp(timeStamp)
        """When value was last set"""

    def set_meta(self, meta):
        # type: (VMeta) -> VMeta
        meta = deserialize_object(meta)
        # Check that the meta attribute_class is ourself
        assert hasattr(meta, "attribute_class"), \
            "Expected meta object, got %r" % meta
        assert isinstance(self, meta.attribute_class), \
            "Meta object needs to be attached to %s, we are a %s" % (
                meta.attribute_class, type(self))
        return self.set_endpoint_data("meta", meta)

    def set_value(self, value, set_alarm_ts=True, alarm=None, ts=None):
        # type: (Any, bool, Alarm, TimeStamp) -> Any
        """Set value, calculating alarm and ts if requested"""
        value = self.meta.validate(value)
        if set_alarm_ts:
            if alarm is None:
                alarm = Alarm.ok
            else:
                alarm = deserialize_object(alarm, Alarm)
            if ts is None:
                ts = TimeStamp()
            else:
                ts = deserialize_object(ts, TimeStamp)
            self.set_value_alarm_ts(value, alarm, ts)
        else:
            self.set_endpoint_data("value", value)
        return self.value

    def set_value_alarm_ts(self, value, alarm, ts):
        """Set value with pre-validated alarm and timeStamp"""
        # type: (Any, Alarm, TimeStamp) -> None
        with self.notifier.changes_squashed:
            # Assume they are of the right format
            self.value = value
            self.notifier.add_squashed_change(self.path + ["value"], value)
            if alarm is not self.alarm:
                self.alarm = alarm
                self.notifier.add_squashed_change(self.path + ["alarm"], alarm)
            self.timeStamp = ts
            self.notifier.add_squashed_change(self.path + ["timeStamp"], ts)

    def set_alarm(self, alarm=None):
        # type: (Alarm) -> Alarm
        if alarm is None:
            alarm = Alarm.ok
        else:
            alarm = deserialize_object(alarm, Alarm)
        return self.set_endpoint_data("alarm", alarm)

    # noinspection PyPep8Naming
    # timeStamp is camelCase to maintain compatibility with EPICS normative
    # types
    def set_timeStamp(self, ts=None):
        # type: (TimeStamp) -> TimeStamp
        if ts is None:
            ts = TimeStamp()
        else:
            ts = deserialize_object(ts, TimeStamp)
        return self.set_endpoint_data("timeStamp", ts)

    def apply_change(self, path, *args):
        if path == ["value"] and args:
            self.set_value(args[0], set_alarm_ts=False)
        else:
            super(AttributeModel, self).apply_change(path, *args)


@Serializable.register_subclass("epics:nt/NTTable:1.0")
class NTTable(AttributeModel):
    """AttributeModel containing a `TableMeta`"""
    __slots__ = []

    def set_value_alarm_ts(self, value, alarm, ts):
        with self.notifier.changes_squashed:
            # Assume they are of the right format
            # Work out what changed in value, do a cheap Array id check
            changed = [k for k in value if value[k] is not self.value[k]]
            self.value = value
            if len(changed) == len(value.call_types):
                # Everything changed
                self.notifier.add_squashed_change(self.path + ["value"], value)
            else:
                # Only some changed
                for k in changed:
                    self.notifier.add_squashed_change(
                        self.path + ["value", k], value[k])
            if alarm is not self.alarm:
                self.alarm = alarm
                self.notifier.add_squashed_change(self.path + ["alarm"], alarm)
            self.timeStamp = ts
            self.notifier.add_squashed_change(self.path + ["timeStamp"], ts)


@Serializable.register_subclass("epics:nt/NTScalarArray:1.0")
class NTScalarArray(AttributeModel):
    """AttributeModel containing a `VArrayMeta`"""
    __slots__ = []


@Serializable.register_subclass("epics:nt/NTScalar:1.0")
class NTScalar(AttributeModel):
    """AttributeModel containing a `StringMeta`, `BooleanMeta`, `NumberMeta`
    or `ChoiceMeta`
    """
    __slots__ = []


@Serializable.register_subclass("epics:nt/NTUnion:1.0")
class NTUnion(AttributeModel):
    """AttributeModel containing a meta producing some object structure"""
    __slots__ = []


FALSE_STRINGS = {'0', 'False', 'false', 'FALSE', 'No', 'no', 'NO'}


@Serializable.register_subclass("malcolm:core/BooleanMeta:1.0")
@VMeta.register_annotype_converter(bool)
class BooleanMeta(VMeta):
    """Meta object containing information for a boolean"""
    attribute_class = NTScalar
    __slots__ = []

    def validate(self, value):
        # type: (Any) -> bool
        """Cast value to boolean and return it"""
        if value in FALSE_STRINGS:
            return False
        else:
            return bool(value)

    def doc_type_string(self):
        # type: () -> str
        return "bool"

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.CHECKBOX
        else:
            return Widget.LED


with Anno("Choices of valid strings"):
    AChoices = Array[str]

UChoices = Union[AChoices, Sequence[Enum], Sequence[str]]


@Serializable.register_subclass("malcolm:core/ChoiceMeta:1.0")
@VMeta.register_annotype_converter(Enum)
class ChoiceMeta(VMeta):
    """Meta object containing information for a enum"""
    attribute_class = NTScalar
    __slots__ = ["choices"]

    def __init__(self, description="", choices=(), tags=(), writeable=False,
                 label=""):
        # type: (AMetaDescription, UChoices, UTags, AWriteable, ALabel) -> None
        super(ChoiceMeta, self).__init__(description, tags, writeable, label)
        self.choices_lookup = {}  # type: Dict[Any, Union[str, Enum]]
        # Used for ChoiceMetaArray subclass only for producing Arrays
        self.enum_cls = None
        self.choices = self.set_choices(choices)

    def set_choices(self, choices):
        # type: (UChoices) -> AChoices
        # Calculate a lookup from all possible entries to the choice value
        choices_lookup = {}  # type: Dict[Any, Union[str, Enum]]
        new_choices = []
        enum_typ = None  # type: Type
        for i, choice in enumerate(choices):
            # If we already have an enum type it must match
            if enum_typ is not None:
                assert isinstance(choice, enum_typ), \
                    "Expected %s choice, got %s" % (enum_typ, choice)
            elif not isinstance(choice, str_):
                enum_typ = type(choice)
            if isinstance(choice, Enum):
                # Our choice value must be a string
                assert isinstance(choice.value, str_), \
                    "Expected Enum choice to have str value, got %r with " \
                    "value %r" % (choice, choice.value)
                # Map the Enum instance and str to the Enum instance
                choices_lookup[choice.value] = choice
                choices_lookup[choice] = choice
                new_choices.append(choice)
            else:
                assert isinstance(choice, str_), \
                    "Expected string choice, got %s" % (choice,)
                # Map the string to itself
                choices_lookup[choice] = choice
                new_choices.append(choice)
            # Map the index to the choice
            choices_lookup[i] = choice
        if choices:
            # Map the default value to the first choice
            choices_lookup[None] = choices[0]
        else:
            # There are no choices, so the default value is the empty string
            choices_lookup[None] = ""
        self.choices_lookup = choices_lookup
        if enum_typ is None or Model.matches_type(enum_typ):
            # We are producing strings
            self.enum_cls = str
        else:
            # We are producing enums
            self.enum_cls = enum_typ
        self.call_types["choices"].typ = self.enum_cls
        return self.set_endpoint_data(
            "choices", self.call_types["choices"](new_choices))

    def validate(self, value):
        # type: (Any) -> Union[Enum, str]
        """Check if the value is valid returns it"""
        # Our lookup table contains all the possible values
        try:
            return self.choices_lookup[value]
        except KeyError:
            raise ValueError(
                "%r is not a valid value in %s" % (value, list(self.choices)))

    def doc_type_string(self):
        # type: () -> str
        return " | ".join([repr(x) for x in self.choices])

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.COMBO
        else:
            return Widget.TEXTUPDATE

    @classmethod
    def from_annotype(cls, anno, writeable, **kwargs):
        # type: (Anno, bool, **Any) -> VMeta
        return super(ChoiceMeta, cls).from_annotype(
            anno, writeable, choices=list(anno.typ))


with Anno("The lower bound of range within which the value must be set"):
    ALimitLow = np.float64
ULimitLow = Union[ALimitLow, float]
with Anno("The upper bound of range within which the value must be set"):
    ALimitHigh = np.float64
ULimitHigh = Union[ALimitHigh, float]
with Anno("Number of significant figures to display"):
    APrecision = np.int32
UPrecision = Union[APrecision, int]
with Anno("The units for the value"):
    AUnits = str


@Serializable.register_subclass("display_t")
class Display(Model):
    __slots__ = ["limitLow", "limitHigh", "description", "precision", "units"]

    # noinspection PyPep8Naming
    # limitLow and limitHigh are camelCase to maintain compatibility with
    # EPICS normative types
    def __init__(self,
                 limitLow=0,  # type: ULimitLow
                 limitHigh=0,  # type: ULimitHigh
                 description="",  # type: AMetaDescription
                 precision=0,  # type: UPrecision
                 units=""  # type: AUnits
                 ):
        # type: (...) -> None
        # Set initial values
        self.limitLow = self.set_limitLow(limitLow)
        self.limitHigh = self.set_limitHigh(limitHigh)
        self.description = self.set_description(description)
        self.precision = self.set_precision(precision)
        self.units = self.set_units(units)

    # noinspection PyPep8Naming
    # limitLow is camelCase to maintain compatibility with EPICS normative
    # types
    def set_limitLow(self, limitLow):
        # type: (ULimitLow) -> ALimitLow
        return self.set_endpoint_data("limitLow", np.float64(limitLow))

    # noinspection PyPep8Naming
    # limitHigh is camelCase to maintain compatibility with EPICS normative
    # types
    def set_limitHigh(self, limitHigh):
        # type: (ULimitHigh) -> ALimitHigh
        return self.set_endpoint_data("limitHigh", np.float64(limitHigh))

    def set_precision(self, precision):
        # type: (UPrecision) -> APrecision
        return self.set_endpoint_data("precision", np.int32(precision))

    def set_units(self, units):
        # type: (AUnits) -> AUnits
        return self.set_endpoint_data("units", units)

    def set_description(self, description):
        # type: (AMetaDescription) -> AMetaDescription
        return self.set_endpoint_data("description", description)


with Anno("Numpy dtype string"):
    ADtype = str
with Anno("Display info meta object"):
    ADisplay = Display

_dtype_strings = ["int8", "uint8", "int16", "uint16", "int32", "uint32",
                  "int64", "uint64", "float32", "float64"]
_dtype_string_lookup = {getattr(np, dtype): dtype for dtype in _dtype_strings}
_dtype_string_lookup.update({int: "int64", float: "float64"})


@Serializable.register_subclass("malcolm:core/NumberMeta:1.0")
@VMeta.register_annotype_converter(list(_dtype_string_lookup))
class NumberMeta(VMeta):
    """Meta object containing information for a numerical value"""
    attribute_class = NTScalar
    __slots__ = ["dtype", "display"]

    def __init__(self,
                 dtype="float64",  # type: ADtype
                 description="",  # type: AMetaDescription
                 tags=(),  # type: UTags
                 writeable=False,  # type: AWriteable
                 label="",  # type: ALabel
                 display=None  # type: ADisplay
                 ):
        # type: (...) -> None
        super(NumberMeta, self).__init__(description, tags, writeable, label)
        # like np.float64
        self._np_type = None  # type: type
        # like "float64"
        self.dtype = self.set_dtype(dtype)
        if display is None:
            # Guess some defaults for the display object
            if dtype in ["float32", "float64"]:
                precision = 8
            else:
                precision = 0
            display = Display(precision=precision)
        self.display = self.set_display(display)

    def set_display(self, display):
        # type: (ADisplay) -> ADisplay
        display = deserialize_object(display, Display)
        return self.set_endpoint_data("display", display)

    def set_dtype(self, dtype):
        # type: (ADtype) -> ADtype
        assert dtype in _dtype_strings, \
            "Expected dtype to be in %s, got %s" % (self._dtypes, dtype)
        self._np_type = getattr(np, dtype)
        return self.set_endpoint_data("dtype", dtype)

    def validate(self, value):
        # type: (Any) -> np.number
        """Check if the value is valid returns it"""
        if value is None:
            value = 0
        cast = self._np_type(value)
        return cast

    def doc_type_string(self):
        # type: () -> str
        return "%s" % self.dtype

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.TEXTINPUT
        else:
            return Widget.TEXTUPDATE

    @classmethod
    def from_annotype(cls, anno, writeable, **kwargs):
        # type: (Anno, bool, **Any) -> VMeta
        return super(NumberMeta, cls).from_annotype(
            anno, writeable, dtype=_dtype_string_lookup[anno.typ])


@Serializable.register_subclass("malcolm:core/StringMeta:1.0")
@VMeta.register_annotype_converter(str)
class StringMeta(VMeta):
    """Meta object containing information for a string"""
    attribute_class = NTScalar
    __slots__ = []

    def validate(self, value):
        # type: (Any) -> str
        """Check if the value is valid returns it"""
        if value is None:
            return ""
        elif isinstance(value, str_):
            return value
        else:
            return str(value)

    def doc_type_string(self):
        # type: () -> str
        return "str"

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.TEXTINPUT
        else:
            return Widget.TEXTUPDATE


class VArrayMeta(VMeta):
    """Intermediate abstract class so `TableMeta` can say "only arrays"
    """
    attribute_class = NTScalarArray
    __slots__ = []


def to_np_array(dtype, value):
    # Give the Array the shorthand version
    if dtype == np.float64:
        dtype = float
    elif dtype == np.int64:
        dtype = int
    if value.__class__ is Array and getattr(value.seq, "dtype", None) == dtype:
        # If Array wraps a numpy array of the correct type we are done
        return value
    else:
        if isinstance(value, Sequence):
            # Cast to numpy array
            value = np.array(value, dtype=dtype)
        return to_array(Array[dtype], value)


@Serializable.register_subclass("malcolm:core/BooleanArrayMeta:1.0")
@VMeta.register_annotype_converter(bool, is_array=True)
class BooleanArrayMeta(VArrayMeta):
    """Meta object containing information for a boolean array"""

    def validate(self, value):
        # type: (Any) -> Array[bool]
        """Check if the value is valid returns it"""
        return to_np_array(bool, value)

    def doc_type_string(self):
        # type: () -> str
        return "[bool]"

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.CHECKBOX
        else:
            return Widget.LED


@Serializable.register_subclass("malcolm:core/ChoiceArrayMeta:1.0")
@VMeta.register_annotype_converter(Enum, is_array=True)
class ChoiceArrayMeta(ChoiceMeta, VArrayMeta):
    """Meta object containing information for a choice array"""

    def validate(self, value):
        # type: (Any) -> Array[str]
        """Check if the value is valid returns it"""
        if value is None:
            return Array[self.enum_cls]()
        else:
            ret = []
            if isinstance(value, str_):
                value = [value]
            # If we have an Array of the right type, start off assuming it's the
            # same
            is_same = value.__class__ is Array and value.typ is self.enum_cls
            for i, choice in enumerate(value):
                # Our lookup table contains all the possible values
                try:
                    new_choice = self.choices_lookup[choice]
                except KeyError:
                    raise ValueError(
                        "%s is not a valid value in %s for element %s" % (
                            value, self.choices, i))
                else:
                    is_same &= choice == new_choice
                    ret.append(new_choice)
            if is_same:
                return value
            else:
                return to_array(Array[self.enum_cls], ret)

    def doc_type_string(self):
        # type: () -> str
        return "[%s]" % super(ChoiceArrayMeta, self).doc_type_string()


@Serializable.register_subclass("malcolm:core/NumberArrayMeta:1.0")
@VMeta.register_annotype_converter(list(_dtype_string_lookup), is_array=True)
class NumberArrayMeta(NumberMeta, VArrayMeta):
    """Meta object containing information for an array of numerical values"""

    def validate(self, value):
        # type: (Any) -> Array
        """Check if the value is valid returns it"""
        return to_np_array(self._np_type, value)

    def doc_type_string(self):
        # type: () -> str
        return "[%s]" % self.dtype


@Serializable.register_subclass("malcolm:core/StringArrayMeta:1.0")
@VMeta.register_annotype_converter(str, is_array=True)
class StringArrayMeta(VArrayMeta):
    """Meta object containing information for a string array"""

    def validate(self, value):
        # type: (Any) -> Array
        """Check if the value is valid returns it"""
        cast = to_array(Array[str], value)
        for v in cast:
            assert isinstance(v, str_), "Expected Array[str], got %r" % (value,)
        return cast

    def doc_type_string(self):
        # type: () -> str
        return "[str]"

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.TEXTINPUT
        else:
            return Widget.TEXTUPDATE


with Anno("Elements that should appear in the table instance"):
    ATableElements = Mapping[str, VArrayMeta]


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
@VMeta.register_annotype_converter(Table)
class TableMeta(VMeta):
    __slots__ = ["elements"]
    attribute_class = NTTable

    def __init__(self,
                 description="",  # type: AMetaDescription
                 tags=(),  # type: UTags
                 writeable=False,  # type: AWriteable
                 label="",  # type: ALabel
                 elements=None,  # type: ATableElements
                 ):
        # type: (...) -> None
        self.table_cls = None  # type: Type[Table]
        self.elements = {}
        super(TableMeta, self).__init__(description, tags, writeable, label)
        # Do this after so writeable is honoured
        self.set_elements(elements if elements else {})

    def set_elements(self, elements):
        # type: (ATableElements) -> ATableElements
        """Set the elements dict from a serialized dict"""
        deserialized = OrderedDict()
        for k, v in elements.items():
            if k != "typeid":
                deserialized[k] = deserialize_object(v, VArrayMeta)
        ret = self.set_endpoint_data("elements", deserialized)
        self.set_table_cls(self.table_cls)
        return ret

    def set_table_cls(self, table_cls=None):
        # type: (Type[Table]) -> None
        if table_cls is None or table_cls.__name__ == "TableSubclass":
            # Either autogenerated by this function or not set, so make one

            class TableSubclass(Table):
                def __init__(self, **kwargs):
                    # type: (**Any) -> None
                    self.__dict__.update(kwargs)

            table_cls = TableSubclass
            for k, meta in self.elements.items():
                # We can distinguish the type by asking for the default
                # validate value
                default_array = meta.validate(None)  # type: Array
                anno = Anno(meta.description, name=k).set_typ(
                    default_array.typ, is_array=True)
                table_cls.call_types[k] = anno
        else:
            # User supplied, check it matches element names
            assert Table.matches_type(table_cls), \
                "Expecting table subclass, got %s" % (table_cls,)
            missing = set(self.elements) - set(table_cls.call_types)
            assert not missing, "Supplied Table missing fields %s" % (missing,)
            extra = set(table_cls.call_types) - set(self.elements)
            assert not extra, "Supplied Table has extra fields %s" % (extra,)
        self.table_cls = table_cls

    def validate(self, value):
        if value is None:
            # Create an empty table
            value = {k: None for k in self.elements}
        elif isinstance(value, Table):
            # Serialize a single level so we can type check it
            value = {k: value[k] for k in value.call_types}
        elif not isinstance(value, dict):
            raise ValueError(
                "Expected Table instance or serialized, got %s" % (value,))
        # We need to make a table instance ourselves
        keys = set(x for x in value if x != "typeid")
        missing = set(self.elements) - keys
        assert not missing, "Supplied table missing fields %s" % (missing,)
        extra = keys - set(self.elements)
        assert not extra, "Supplied table has extra fields %s" % (extra,)
        args = {k: meta.validate(value[k]) for k, meta in self.elements.items()}
        value = self.table_cls(**args)
        # Check column lengths
        value.validate_column_lengths()
        # Check the table class give Array elements
        for k in args:
            assert value[k].__class__ is Array, \
                "Table Class %s doesn't wrap attr '%s' with an Array" % (
                    self.table_cls, k)
        return value

    def doc_type_string(self):
        # type: () -> str
        return "`Table`"

    def default_widget(self):
        # type: () -> Widget
        return Widget.TABLE

    @classmethod
    def from_table(cls, table_cls, description, widget=None, writeable=(),
                   extra_tags=()):
        """Create a TableMeta object, using a Table subclass as the spec

        Args:
            table_cls: The Table class to read __init__ args from
            description: The description of the created Meta
            widget: The widget of the created Meta
            writeable: A list of the writeable field names. If there are any
                writeable fields then the whole Meta is writeable
            extra_tags: A list of tags to be added to the table meta
            """
        # type: (Type[Table], str, Widget, List[str], List[str]) -> TableMeta
        elements = OrderedDict()
        for k, ct in table_cls.call_types.items():
            subclass = cls.lookup_annotype_converter(ct)
            elements[k] = subclass.from_annotype(ct, writeable=k in writeable)
        ret = cls(description=description, elements=elements,
                  writeable=bool(writeable))
        if widget is None:
            widget = ret.default_widget()
        tags = [widget.tag()]
        tags.extend(extra_tags)
        ret.set_tags(tags)
        ret.set_table_cls(table_cls)
        return ret

    @classmethod
    def from_annotype(cls, anno, writeable, **kwargs):
        # type: (Anno, bool, **Any) -> VMeta
        assert Table.matches_type(anno.typ), \
            "Expected Table, got %s" % anno.typ
        if writeable:
            # All fields are writeable
            writeable = list(anno.typ.call_types)
        else:
            # No fields are writeable
            writeable = []
        return cls.from_table(anno.typ, anno.description, writeable=writeable)


# Types used when deserializing to the class
with Anno("Meta objects that are used to describe the elements in the map"):
    AElements = Mapping[str, VMeta]
with Anno("The required elements in the map"):
    ARequired = Array[str]

# A more permissive union to allow a wider range of set_* args
URequired = Union[ARequired, Sequence[str], str]


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Model):
    """An object containing a set of ScalarMeta objects"""
    __slots__ = ["elements", "required"]

    def __init__(self,
                 elements=None,  # type: Optional[AElements]
                 required=()  # type: URequired
                 ):
        # type: (...) -> None
        self.elements = self.set_elements(elements if elements else {})
        self.required = self.set_required(required)

    def set_elements(self, elements):
        # type: (AElements) -> AElements
        deserialized = OrderedDict()
        for k, v in elements.items():
            if k != "typeid":
                v = deserialize_object(v, VMeta)
                if not v.label:
                    v.set_label(camel_to_title(k))
                deserialized[k] = v
        return self.set_endpoint_data("elements", deserialized)

    def set_required(self, required):
        # type: (URequired) -> ARequired
        for r in required:
            assert r in self.elements, \
                "Expected one of %r, got %r" % (list(self.elements), r)
        return self.set_endpoint_data("required", ARequired(required))

    def validate(self, param_dict=None, add_missing=False):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Return a param dict in the right order, with the correct keys and
        values of the correct type with no extras or missing"""
        if param_dict is None:
            param_dict = {}
        extra = set(param_dict) - set(self.elements)
        assert not extra, \
            "Given keys %s, some of which aren't in allowed keys %s" % (
                list(sorted(param_dict)), list(self.elements))
        args = OrderedDict()
        for k, m in self.elements.items():
            if k in param_dict:
                args[k] = m.validate(param_dict[k])
            elif add_missing:
                args[k] = m.validate(None)
        missing = set(self.required) - set(args)
        assert not missing, \
            "Requires keys %s but only given %s" % (
                list(self.required), list(args))
        return args


# Types used when deserializing to the class
with Anno("Meta for describing the arguments that should be passed"):
    ATakes = MapMeta
with Anno("The required elements in the map"):
    ADefaults = Mapping[str, Any]
with Anno("Meta for describing the arguments that will be returned"):
    AReturns = MapMeta


@Serializable.register_subclass("malcolm:core/MethodMeta:1.1")
class MethodMeta(Meta):
    """Exposes a function with metadata for arguments and return values"""
    __slots__ = ["takes", "returns", "defaults"]

    def __init__(self,
                 takes=None,  # type: Optional[ATakes]
                 defaults=None,  # type: Optional[ADefaults]
                 description="",  # type: AMetaDescription
                 tags=(),  # type: UTags
                 writeable=False,  # type: AWriteable
                 label="",  # type: ALabel
                 returns=None,  # type: Optional[AReturns]
                 ):
        # type: (...) -> None
        self.takes = self.set_takes(takes if takes else MapMeta())
        self.returns = self.set_returns(returns if returns else MapMeta())
        self.defaults = self.set_defaults(defaults if defaults else {})
        super(MethodMeta, self).__init__(description, tags, writeable, label)

    def set_takes(self, takes):
        # type: (ATakes) -> ATakes
        takes = deserialize_object(takes, MapMeta)
        return self.set_endpoint_data("takes", takes)

    def set_defaults(self, defaults):
        # type: (ADefaults) -> ADefaults
        defaults = FrozenOrderedDict(tuple(
            (k, self.takes.elements[k].validate(v))
            for k, v in defaults.items() if k != "typeid"
        ))
        return self.set_endpoint_data("defaults", defaults)

    def set_returns(self, returns):
        # type: (AReturns) -> AReturns
        returns = deserialize_object(returns, MapMeta)
        return self.set_endpoint_data("returns", returns)

    @classmethod
    def from_callable(cls, func, description=None, returns=True,
                      without_takes=()):
        # type: (Callable, str, bool, Sequence[str]) -> MethodMeta
        """Return an instance of this class from a Callable

        Args:
            func: @with_call_types decorated Callable to inspect
            description: Override description. If None use func.__doc__
            returns: If True then scan return_type too
            without_takes: A sequence of strings that should not appear in the
                takes structure

        Returns:
            A MethodMeta with takes and returns matching the input func
        """
        if description is None:
            if func.__doc__ is None:
                description = ""
            else:
                description = func.__doc__
        method = cls(description=description)
        tags = []
        takes_elements = OrderedDict()
        defaults = OrderedDict()
        takes_required = []
        without_takes_set = set(without_takes)
        for k, anno in getattr(func, "call_types", {}).items():
            if k in without_takes_set:
                continue
            scls = VMeta.lookup_annotype_converter(anno)
            takes_elements[k] = scls.from_annotype(anno, writeable=True)
            if anno.default is NO_DEFAULT:
                takes_required.append(k)
            elif anno.default is not None:
                defaults[k] = anno.default
        takes = MapMeta(elements=takes_elements, required=takes_required)
        method.set_takes(takes)
        method.set_defaults(defaults)
        if returns:
            returns_elements = OrderedDict()
            returns_required = []
            return_type = getattr(func, "return_type", None)  # type: Anno
            if return_type is None or return_type.typ is None:
                call_types = {}
            elif WithCallTypes.matches_type(return_type.typ):
                call_types = return_type.typ.call_types
            else:
                tags.append(method_return_unpacked())
                call_types = {"return": return_type}
            for k, anno in call_types.items():
                scls = VMeta.lookup_annotype_converter(anno)
                returns_elements[k] = scls.from_annotype(anno, writeable=False)
                if anno.default is not None:
                    returns_required.append(k)
            returns = MapMeta(
                elements=returns_elements, required=returns_required)
            method.set_returns(returns)
        method.set_tags(tags)
        return method


# Types used when deserializing to the class
with Anno("The last map this took/returned"):
    AMVValue = Mapping[str, Any]
with Anno("The elements that were supplied in the map"):
    APresent = Array[str]

# A more permissive union to allow a wider range of set_* args
UPresent = Union[APresent, Sequence[str], str]


@Serializable.register_subclass("malcolm:core/MethodLog:1.0")
class MethodLog(Model):
    """Exposes a function with metadata for arguments and return values"""
    __slots__ = ["value", "alarm", "timeStamp"]

    # noinspection PyPep8Naming
    # timeStamp is camelCase to maintain compatibility with EPICS normative
    # types
    def __init__(self, value=None, present=(), alarm=None, timeStamp=None):
        # type: (AMVValue, UPresent, AAlarm, ATimeStamp) -> None
        self.value = self.set_value(value)
        self.present = self.set_present(present)
        self.alarm = self.set_alarm(alarm)
        self.timeStamp = self.set_timeStamp(timeStamp)

    def set_value(self, value=None):
        # type: (AMVValue) -> AMVValue
        if value is None:
            value = {}
        return self.set_endpoint_data("value", value)

    def set_present(self, present):
        # type: (UPresent) -> APresent
        return self.set_endpoint_data("present", APresent(present))

    def set_alarm(self, alarm=None):
        # type: (Alarm) -> Alarm
        if alarm is None:
            alarm = Alarm.ok
        else:
            alarm = deserialize_object(alarm, Alarm)
        return self.set_endpoint_data("alarm", alarm)

    # noinspection PyPep8Naming
    # timeStamp is camelCase to maintain compatibility with EPICS normative
    # types
    def set_timeStamp(self, ts=None):
        # type: (TimeStamp) -> TimeStamp
        if ts is None:
            ts = TimeStamp()
        else:
            ts = deserialize_object(ts, TimeStamp)
        return self.set_endpoint_data("timeStamp", ts)


# Types used when deserializing to the class
with Anno("The last arguments that a method call took"):
    ATook = MethodLog
with Anno("The last return value produced by a method call"):
    AReturned = MethodLog
with Anno("Meta for describing the arguments that will be returned"):
    AMethodMeta = MethodMeta


@Serializable.register_subclass("malcolm:core/Method:1.1")
class MethodModel(Model):
    """Exposes a function with last took and returned arguments"""
    __slots__ = ["took", "returned", "meta"]

    def __init__(self, took=None, returned=None, meta=None):
        # type: (ATook, AReturned, AMethodMeta) -> None
        self.meta = self.set_meta(meta if meta else MethodMeta())
        self.took = self.set_took(took)
        self.returned = self.set_returned(returned)

    def set_meta(self, meta):
        # type: (AMethodMeta) -> AMethodMeta
        meta = deserialize_object(meta, MethodMeta)
        return self.set_endpoint_data("meta", meta)

    def set_took(self, took=None):
        # type: (ATook) -> ATook
        if took is None:
            took = MethodLog(self.meta.takes.validate(add_missing=True),
                             [], Alarm.ok, TimeStamp.zero)
        else:
            took = deserialize_object(took, MethodLog)
        return self.set_endpoint_data("took", took)

    def set_returned(self, returned=None):
        # type: (AReturned) -> AReturned
        if returned is None:
            returned = MethodLog(self.meta.returns.validate(add_missing=True),
                                 [], Alarm.ok, TimeStamp.zero)
        else:
            returned = deserialize_object(returned, MethodLog)
        return self.set_endpoint_data("returned", returned)


# Types used when deserializing to the class
with Anno("The list of fields currently in the Block"):
    AFields = Array[str]

# A more permissive union to allow a wider range of set_* args
UFields = Union[AFields, Sequence[str], str]


@Serializable.register_subclass("malcolm:core/BlockMeta:1.0")
class BlockMeta(Meta):
    __slots__ = ["fields"]

    def __init__(self,
                 description="",  # type: AMetaDescription
                 tags=(),  # type: UTags
                 writeable=True,  # type: AWriteable
                 label="",  # type: ALabel
                 fields=(),  # type: UFields
                 ):
        # type: (...) -> None
        super(BlockMeta, self).__init__(description, tags, writeable, label)
        self.fields = self.set_fields(fields)

    def set_fields(self, fields):
        # type: (UFields) -> AFields
        return self.set_endpoint_data("fields", AFields(fields))


# Anything that can be a child of a Block (or converted to one)
ModelOrDict = Union[AttributeModel, MethodModel, BlockMeta, Mapping[str, Any]]


@Serializable.register_subclass("malcolm:core/Block:1.0")
class BlockModel(Model):
    """Data Model for a Block"""

    def __init__(self):
        # type: () -> None
        # Make a new call_types dict so we don't modify for all instances
        self.call_types = OrderedDict()
        self.meta = self.set_endpoint_data("meta", BlockMeta())

    def set_endpoint_data(self, name, value):
        # type: (str, ModelOrDict) -> Any
        name = deserialize_object(name, str_)
        if name == "meta":
            value = deserialize_object(value, BlockMeta)
        else:
            value = deserialize_object(value, (AttributeModel, MethodModel))
        with self.notifier.changes_squashed:
            if name in self.call_types:
                # Stop the old Model notifying
                getattr(self, name).set_notifier_path(Model.notifier, [])
            else:
                anno = Anno("Field").set_typ(type(value))
                self.call_types[name] = anno
            value.set_notifier_path(self.notifier, self.path + [name])
            setattr(self, name, value)
            # Tell the notifier what changed
            self.notifier.add_squashed_change(self.path + [name], value)
            self._update_fields()
            return value

    def _update_fields(self):
        self.meta.set_fields([x for x in self.call_types if x != "meta"])

    def remove_endpoint(self, name):
        # type: (str) -> None
        with self.notifier.changes_squashed:
            getattr(self, name).set_notifier_path(Model.notifier, [])
            self.call_types.pop(name)
            delattr(self, name)
            self._update_fields()
            self.notifier.add_squashed_delete(self.path + [name])
