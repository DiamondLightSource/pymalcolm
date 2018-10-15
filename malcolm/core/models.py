import inspect

from annotypes import Array, Anno, Union, Sequence, Mapping, Any, to_array, \
    Optional, TYPE_CHECKING, WithCallTypes, NO_DEFAULT
import numpy as np
from enum import Enum

from malcolm.compat import OrderedDict, str_
from .alarm import Alarm
from .notifier import DummyNotifier, Notifier
from .serializable import Serializable, deserialize_object, camel_to_title
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
                if issubclass(ct.typ[1], Model) and child:
                    for k, v in getattr(self, name).items():
                        v.set_notifier_path(notifier, self.path + [name, k])
            elif issubclass(ct.typ, Model):
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
                assert not issubclass(ct.typ, Model), \
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
                if issubclass(ct.typ[1], Model):
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
                if issubclass(ct.typ, Model):
                    # If we have an old Model then stop it notifying
                    child = getattr(self, name, None)
                    if child:
                        child.set_notifier_path(Model.notifier, [])
                    value.set_notifier_path(self.notifier, self.path)
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
        self.value = self.set_value(value, set_alarm_ts=False)
        self.alarm = self.set_alarm(alarm)
        self.timeStamp = self.set_ts(timeStamp)

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

    def set_ts(self, ts=None):
        # type: (TimeStamp) -> TimeStamp
        if ts is None:
            ts = TimeStamp()
        else:
            ts = deserialize_object(ts, TimeStamp)
        return self.set_endpoint_data("timeStamp", ts)

    def apply_change(self, path, *args):
        if path == ["value"] and args:
            self.set_value(args[0], set_alarm_ts=False)
        elif path == ["timeStamp"] and args:
            self.set_ts(args[0])
        else:
            super(AttributeModel, self).apply_change(path, *args)


@Serializable.register_subclass("epics:nt/NTTable:1.0")
class NTTable(AttributeModel):
    __slots__ = []

    def to_dict(self):
        # type: () -> OrderedDict
        d = OrderedDict()
        d["typeid"] = self.typeid
        # Add labels for compatibility with epics normative types
        labels = []
        for column_name in self.meta.elements:
            column_meta = self.meta.elements[column_name]
            if column_meta.label:
                labels.append(column_meta.label)
            else:
                labels.append(column_name)
        d["labels"] = Array[str](labels)
        d.update(super(NTTable, self).to_dict())
        return d

    @classmethod
    def from_dict(cls, d, ignore=()):
        ignore += ("labels",)
        return super(NTTable, cls).from_dict(d, ignore)


@Serializable.register_subclass("epics:nt/NTUnion:1.0")
class NTUnion(AttributeModel):
    __slots__ = []


@Serializable.register_subclass("epics:nt/NTScalarArray:1.0")
class NTScalarArray(AttributeModel):
    __slots__ = []


@Serializable.register_subclass("epics:nt/NTScalar:1.0")
class NTScalar(AttributeModel):
    __slots__ = []


@Serializable.register_subclass("malcolm:core/BooleanMeta:1.0")
@VMeta.register_annotype_converter(bool)
class BooleanMeta(VMeta):
    """Meta object containing information for a boolean"""
    attribute_class = NTScalar
    __slots__ = []

    def validate(self, value):
        # type: (Any) -> bool
        """Cast value to boolean and return it"""
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
        str_choices = []
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
                str_choices.append(choice.value)
            else:
                assert isinstance(choice, str_), \
                    "Expected string choice, got %s" % (choice,)
                # Map the string to itself
                choices_lookup[choice] = choice
                str_choices.append(choice)
            # Map the index to the choice
            choices_lookup[i] = choice
        if choices:
            # Map the default value to the first choice
            choices_lookup[None] = choices[0]
        else:
            # There are no choices, so the default value is the empty string
            choices_lookup[None] = ""
        if enum_typ is None or issubclass(enum_typ, str_):
            # We are producing strings
            self.enum_cls = str
        else:
            # We are producing enums
            self.enum_cls = enum_typ
        self.choices_lookup = choices_lookup
        return self.set_endpoint_data("choices", AChoices(str_choices))

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


with Anno("Numpy dtype string"):
    ADtype = str


_dtype_strings = ["int8", "uint8", "int16", "uint16", "int32", "uint32", "int64",
           "uint64", "float32", "float64"]
_dtype_string_lookup = {getattr(np, dtype): dtype for dtype in _dtype_strings}
_dtype_string_lookup.update({int: "int64", float: "float64"})


@Serializable.register_subclass("malcolm:core/NumberMeta:1.0")
@VMeta.register_annotype_converter(list(_dtype_string_lookup))
class NumberMeta(VMeta):
    """Meta object containing information for a numerical value"""
    attribute_class = NTScalar
    __slots__ = ["dtype"]

    def __init__(self, dtype="float64", description="", tags=(),
                 writeable=False, label=""):
        # type: (ADtype, AMetaDescription, UTags, AWriteable, ALabel) -> None
        super(NumberMeta, self).__init__(description, tags, writeable, label)
        # like np.float64
        self._np_type = None  # type: type
        # like "float64"
        self.dtype = self.set_dtype(dtype)

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
    # intermediate class so TableMeta can say "only arrays"
    attribute_class = NTScalarArray
    __slots__ = []


def to_np_array(dtype, value):
    # Give the Array the shorthand version
    if dtype == np.float64:
        dtype = float
    elif dtype == np.int64:
        dtype = int
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
            for i, choice in enumerate(value):
                # Our lookup table contains all the possible values
                try:
                    ret.append(self.choices_lookup[choice])
                except KeyError:
                    raise ValueError(
                        "%s is not a valid value in %s for element %s" % (
                            value, self.choices, i))
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
                anno = Anno(meta.description, default_array.typ, k)
                anno.is_array = True
                anno.is_mapping = False
                table_cls.call_types[k] = anno
        else:
            # User supplied, check it matches element names
            assert issubclass(table_cls, Table), \
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
            # Serialize it so we can type check it
            value = value.to_dict()
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
        return value

    def doc_type_string(self):
        # type: () -> str
        return "`Table`"

    def default_widget(self):
        # type: () -> Widget
        return Widget.TABLE

    @classmethod
    def from_table(cls, table_cls, description, widget=None, writeable=()):
        """Create a TableMeta object, using a Table subclass as the spec

        Args:
            table_cls: The Table class to read __init__ args from
            description: The description of the created Meta
            widget: The widget of the created Meta
            writeable: A list of the writeable field names. If there are any
                writeable fields then the whole Meta is writeable
            """
        # type: (Type[Table], str, Widget, List[str]) -> TableMeta
        elements = OrderedDict()
        for k, ct in table_cls.call_types.items():
            subclass = cls.lookup_annotype_converter(ct)
            elements[k] = subclass.from_annotype(ct, writeable=k in writeable)
        ret = cls(description=description, elements=elements,
                  writeable=bool(writeable))
        if widget is None:
            widget = ret.default_widget()
        ret.set_tags([widget.tag()])
        ret.set_table_cls(table_cls)
        return ret

    @classmethod
    def from_annotype(cls, anno, writeable, **kwargs):
        # type: (Anno, bool, **Any) -> VMeta
        assert issubclass(anno.typ, Table), \
            "Expected Table, got %s" % anno.typ
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


# Types used when deserializing to the class
with Anno("Meta for describing the arguments that should be passed"):
    ATakes = MapMeta
with Anno("The required elements in the map"):
    ADefaults = Mapping[str, Any]
with Anno("Meta for describing the arguments that will be returned"):
    AReturns = MapMeta


@Serializable.register_subclass("malcolm:core/Method:1.0")
class MethodModel(Meta):
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
        super(MethodModel, self).__init__(description, tags, writeable, label)

    def set_takes(self, takes):
        # type: (ATakes) -> ATakes
        takes = deserialize_object(takes, MapMeta)
        return self.set_endpoint_data("takes", takes)

    def set_defaults(self, defaults):
        # type: (ADefaults) -> ADefaults
        for k, v in defaults.items():
            if k != "typeid":
                defaults[k] = self.takes.elements[k].validate(v)
        return self.set_endpoint_data("defaults", defaults)

    def set_returns(self, returns):
        # type: (AReturns) -> AReturns
        returns = deserialize_object(returns, MapMeta)
        return self.set_endpoint_data("returns", returns)

    def validate(self, param_dict=None):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        if param_dict is None:
            param_dict = {}
        args = {}
        for k, v in param_dict.items():
            assert k in self.takes.elements, \
                "Method passed argument %r which is not in %r" % (
                    k, list(self.takes.elements))
            args[k] = self.takes.elements[k].validate(v)
        missing = set(self.takes.required) - set(args)
        assert not missing, \
            "Method requires %s but only passed %s" % (
                list(self.takes.required), list(args))
        return args

    @classmethod
    def from_callable(cls, func, description=None, returns=True):
        # type: (Callable, str, bool) -> MethodModel
        """Return an instance of this class from a Callable"""
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
        for k, anno in getattr(func, "call_types", {}).items():
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
            elif issubclass(return_type.typ, WithCallTypes):
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
                anno = Anno("Field", typ=type(value))
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
            self.notifier.add_squashed_change(self.path + [name])
