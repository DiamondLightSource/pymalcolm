from annotypes import Array, Anno, Union, Sequence, Mapping, Any, \
    TYPE_CHECKING, to_array
import numpy as np

from malcolm.compat import OrderedDict, str_
from .alarm import Alarm
from .model import Model
from .serializable import Serializable, deserialize_object, camel_to_title
from .table import Table
from .tags import Widget
from .timestamp import TimeStamp

if not TYPE_CHECKING:
    from typing import Type

# Types used when deserializing to the class
with Anno("Description of what this element represents"):
    Description = str
with Anno("Generic text tags for client tools to interpret"):
    Tags = Array[str]
with Anno("Whether this element is currently writeable"):
    Writeable = bool
with Anno("A human readable label for the element"):
    Label = str

# A more permissive union to allow a wider range of set_* args
UTags = Union[Tags, Sequence[str], str]


class Meta(Model):
    """Base class for describing Blocks, Methods and Attributes"""
    __slots__ = ["description", "tags", "writeable", "label"]

    def __init__(self, description="", tags=(), writeable=False, label=""):
        # type: (Description, UTags, Writeable, Label) -> None
        self.description = self.set_description(description)
        self.tags = self.set_tags(tags)
        self.writeable = self.set_writeable(writeable)
        self.label = self.set_label(label)

    def set_description(self, description):
        # type: (Description) -> Description
        return self.set_endpoint_data("description", description)

    def set_tags(self, tags):
        # type: (UTags) -> Tags
        return self.set_endpoint_data("tags", Tags(tags))

    def set_writeable(self, writeable):
        # type: (Writeable) -> Writeable
        return self.set_endpoint_data("writeable", writeable)

    def set_label(self, label):
        # type: (Label) -> Label
        return self.set_endpoint_data("label", label)


class VMeta(Meta):
    """Abstract base class for validating the values of Attributes"""
    attribute_class = None
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
        attr = self.attribute_class(self, initial_value)
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


# Types used when deserializing to the class
with Anno("The current value of the Attribute"):
    Value = Any
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

    def __init__(self, value=None, alarm=None, timeStamp=None, meta=None):
        # type: (Value, AAlarm, ATimeStamp, AVMeta) -> None
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
            self.alarm = alarm
            self.notifier.add_squashed_change(self.path + ["alarm"], alarm)
            self.timeStamp = ts
            self.notifier.add_squashed_change(self.path + ["timeStamp"], ts)

    def set_alarm(self, alarm=None):
        # type: (Alarm) -> Alarm
        if alarm is None:
            alarm = Alarm.ok
        return self.set_endpoint_data("alarm", alarm)

    def set_ts(self, ts=None):
        # type: (TimeStamp) -> TimeStamp
        if ts is None:
            ts = TimeStamp()
        return self.set_endpoint_data("timeStamp", ts)


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
        d["labels"] = labels
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
    Choices = Array[str_]


@Serializable.register_subclass("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(VMeta):
    """Meta object containing information for a enum"""
    attribute_class = NTScalar
    __slots__ = ["choices"]

    def __init__(self, description="", choices=(), tags=(), writeable=False,
                 label=""):
        # type: (Description, Choices, Tags, Writeable, Label) -> None
        super(ChoiceMeta, self).__init__(description, tags, writeable, label)
        self.choices = self.set_choices(choices)

    def set_choices(self, choices):
        # type: (Choices) -> Choices
        choices = Choices(choices)
        return self.set_endpoint_data("choices", choices)

    def validate(self, value):
        # type: (Any) -> str_
        """Check if the value is valid returns it"""
        if value is None:
            if self.choices:
                return self.choices[0]
            else:
                return ""
        elif value in self.choices:
            return value
        elif isinstance(value, int) and value < len(self.choices):
            return self.choices[value]
        else:
            raise ValueError(
                "%s is not a valid value in %s" % (value, self.choices))

    def doc_type_string(self):
        # type: () -> str
        return " | ".join([repr(x) for x in self.choices])

    def default_widget(self):
        # type: () -> Widget
        if self.writeable:
            return Widget.COMBO
        else:
            return Widget.TEXTUPDATE


with Anno("Numpy dtype string"):
    Dtype = str_


@Serializable.register_subclass("malcolm:core/NumberMeta:1.0")
class NumberMeta(VMeta):
    """Meta object containing information for a numerical value"""
    attribute_class = NTScalar
    __slots__ = ["dtype"]
    _dtypes = ["int8", "uint8", "int16", "uint16", "int32", "uint32", "int64",
               "uint64", "float32", "float64"]

    def __init__(self, dtype="float64", description="", tags=(),
                 writeable=False, label=""):
        # type: (Dtype, Description, Tags, Writeable, Label) -> None
        super(NumberMeta, self).__init__(description, tags, writeable, label)
        # like np.float64
        self._np_dtype = None
        # like "float64"
        self.dtype = self.set_dtype(dtype)

    def set_dtype(self, dtype):
        # type: (Dtype) -> Dtype
        assert dtype in self._dtypes, \
            "Expected dtype to be in %s, got %s" % (self._dtypes, dtype)
        self._np_dtype = getattr(np, dtype)
        return self.set_endpoint_data("dtype", dtype)

    def validate(self, value):
        # type: (Any) -> np.number
        """Check if the value is valid returns it"""
        if value is None:
            value = 0
        cast = self._np_dtype(value)
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


@Serializable.register_subclass("malcolm:core/StringMeta:1.0")
class StringMeta(VMeta):
    """Meta object containing information for a string"""
    attribute_class = NTScalar
    __slots__ = []

    def validate(self, value):
        # type: (Any) -> str_
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


@Serializable.register_subclass("malcolm:core/BooleanArrayMeta:1.0")
class BooleanArrayMeta(VArrayMeta):
    """Meta object containing information for a boolean array"""

    def validate(self, value):
        # type: (Any) -> Array[bool]
        """Check if the value is valid returns it"""
        return to_array(Array[bool], value)

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
class ChoiceArrayMeta(ChoiceMeta, VArrayMeta):
    """Meta object containing information for a choice array"""

    def validate(self, value):
        # type: (Any) -> Array[str_]
        """Check if the value is valid returns it"""
        if value is None:
            return Array[str]()
        if isinstance(value, str_):
            raise ValueError("Expected iterable of strings, got %r" % value)
        else:
            for i, choice in enumerate(value):
                if choice not in self.choices:
                    raise ValueError("%s is not a valid value for element %s" %
                                     (choice, i))
            return to_array(Array[str], value)

    def doc_type_string(self):
        # type: () -> str
        return "[%s]" % super(ChoiceArrayMeta, self).doc_type_string()


@Serializable.register_subclass("malcolm:core/NumberArrayMeta:1.0")
class NumberArrayMeta(NumberMeta, VArrayMeta):
    """Meta object containing information for an array of numerical values"""
    def validate(self, value):
        # type: (Any) -> Array
        """Check if the value is valid returns it"""
        return to_array(Array[self.dtype], value)

    def doc_type_string(self):
        # type: () -> str
        return "[%s]" % self.dtype


@Serializable.register_subclass("malcolm:core/StringArrayMeta:1.0")
class StringArrayMeta(VArrayMeta):
    """Meta object containing information for a string array"""

    def validate(self, value):
        # type: (Any) -> Array
        """Check if the value is valid returns it"""
        return to_array(Array[str_], value)

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
    TElements = Mapping[str_, VArrayMeta]


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):
    __slots__ = ["elements"]
    attribute_class = NTTable

    def __init__(self, description="", tags=(), writeable=False, label="",
                 elements=None):
        # type: (Description, Tags, Writeable, Label, TElements) -> None
        super(TableMeta, self).__init__(description, tags, writeable, label)
        self.elements = self.set_elements(elements if elements else {})

    def set_elements(self, elements):
        # type: (TElements) -> TElements
        """Set the elements dict from a serialized dict"""
        deserialized = OrderedDict()
        for k, v in elements.items():
            if k != "typeid":
                deserialized[k] = deserialize_object(v, VArrayMeta)
        return self.set_endpoint_data("elements", deserialized)

    def validate(self, value):
        if value is None:
            value = {}
        if isinstance(value, Table):
            # We already have a table instance, check it has the right
            # call_type args
            missing = set(self.elements) - set(value.call_types)
            assert not missing, "Supplied table missing fields %s" % (missing,)
            extra = set(value.call_types) - set(self.elements)
            assert not extra, "Supplied table has extra fields %s" % (extra,)
            for field, anno in value.call_types.items():
                assert anno.is_array, "Anno %s isn't an array" % (anno,)
                meta = self.elements[field]
                if anno.typ == bool:
                    assert isinstance(meta, BooleanArrayMeta), \
                        "Expected BooleanArrayMeta for %s, got %s" % (
                            field, meta)
                elif anno.typ == str:
                    assert isinstance(meta, StringArrayMeta), \
                        "Expected StringArrayMeta for %s, got %s" % (
                            field, meta)
                else:
                    assert isinstance(meta, NumberArrayMeta), \
                        "Expected NumberArrayMeta for %s, got %s" % (
                            field, meta)
                    assert np.dtype(meta.dtype) == anno.typ, \
                        "Expected dtype %s for %s, got %s" % (
                            meta.dtype, field, anno.typ)
        else:
            # We need to make a table class and instantiate it ourselves
            keys = set(value)
            keys.remove("typeid")
            missing = set(self.elements) - keys
            assert not missing, "Supplied table missing fields %s" % (missing,)
            extra = keys - set(self.elements)
            assert not extra, "Supplied table has extra fields %s" % (extra,)

            class TableInstance(Table):
                pass

            for field, meta in self.elements.items():
                setattr(TableInstance, field, meta.validate(value[field]))

            value = TableInstance()
        # Check column lengths
        value.validate_column_lengths()
        return value

    def doc_type_string(self):
        # type: () -> str
        return "`Table`"

    def default_widget(self):
        # type: () -> Widget
        return Widget.TABLE


# Types used when deserializing to the class
with Anno("Meta objects that are used to describe the elements in the map"):
    Elements = Mapping[str_, VMeta]
with Anno("The required elements in the map"):
    Required = Array[str_]

# A more permissive union to allow a wider range of set_* args
URequired = Union[Required, Sequence[str_], str_]


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Meta):
    """An object containing a set of ScalarMeta objects"""
    __slots__ = ["elements", "required"]

    def __init__(self,
                 elements=None,  # type: Optional[Elements]
                 description="",  # type: Description
                 tags=(),  # type: UTags
                 writeable=False,   # type: Writeable
                 label="",  # type: Label
                 required=()  # type: URequired
                 ):
        super(MapMeta, self).__init__(description, tags, writeable, label)
        self.elements = self.set_elements(elements if elements else {})
        self.required = self.set_required(required)

    def set_elements(self, elements):
        # type: (Elements) -> Elements
        deserialized = OrderedDict()
        for k, v in elements.items():
            if k != "typeid":
                v = deserialize_object(v, VMeta)
                if not v.label:
                    v.set_label(camel_to_title(k))
                deserialized[k] = v
        return self.set_endpoint_data("elements", deserialized)

    def set_required(self, required):
        # type: (Required) -> Required
        for r in required:
            assert r in self.elements, \
                "Expected one of %r, got %r" % (list(self.elements), r)
        return self.set_endpoint_data("required", Required(required))


# Types used when deserializing to the class
with Anno("Meta for describing the arguments that should be passed"):
    Takes = MapMeta
with Anno("The required elements in the map"):
    Defaults = Mapping[str_, Any]
with Anno("Meta for describing the arguments that will be returned"):
    Returns = MapMeta


@Serializable.register_subclass("malcolm:core/Method:1.0")
class MethodModel(Meta):
    """Exposes a function with metadata for arguments and return values"""
    __slots__ = ["takes", "returns", "defaults"]

    def __init__(self,
                 takes=None,  # type: Optional[Takes]
                 defaults=None,  # type: Optional[Defaults]
                 description="",  # type: Description
                 tags=(),  # type: UTags
                 writeable=False,  # type: Writeable
                 label="",  # type: Label
                 returns=None,  # type: Optional[Returns]
                 ):
        super(MethodModel, self).__init__(description, tags, writeable, label)
        self.takes = self.set_takes(takes if takes else MapMeta())
        self.returns = self.set_returns(returns if returns else MapMeta())
        self.defaults = self.set_defaults(defaults if defaults else {})

    def set_takes(self, takes):
        # type: (Takes) -> Takes
        takes = deserialize_object(takes, MapMeta)
        return self.set_endpoint_data("takes", takes)

    def set_defaults(self, defaults):
        # type: (Defaults) -> Defaults
        for k, v in defaults.items():
            if k != "typeid":
                defaults[k] = self.takes.elements[k].validate(v)
        return self.set_endpoint_data("defaults", defaults)

    def set_returns(self, returns):
        # type: (Returns) -> Returns
        returns = deserialize_object(returns, MapMeta)
        return self.set_endpoint_data("returns", returns)


# Types used when deserializing to the class
with Anno("The list of fields currently in the Block"):
    Fields = Array[str]

# A more permissive union to allow a wider range of set_* args
UFields = Union[Fields, Sequence[str], str]


@Serializable.register_subclass("malcolm:core/BlockMeta:1.0")
class BlockMeta(Meta):
    __slots__ = ["fields"]

    def __init__(self,
                 description="",  # type: Description
                 tags=(),  # type: UTags
                 writeable=False,  # type: Writeable
                 label="",  # type: Label
                 fields=(),  # type: UFields
                 ):
        # type: (...) -> None
        super(BlockMeta, self).__init__(description, tags, writeable, label)
        self.fields = self.set_fields(fields)

    def set_fields(self, fields):
        # type: (UFields) -> Fields
        return self.set_endpoint_data("fields", Fields(fields))


@Serializable.register_subclass("malcolm:core/Block:1.0")
class BlockModel(Model):
    """Data Model for a Block"""

    def __init__(self):
        # Make a new call_types dict so we don't modify for all instances
        self.call_types = OrderedDict()
        self.meta = self.set_endpoint_data("meta", BlockMeta())

    def set_endpoint_data(self, name, value):
        # type: (str_, Any) -> Any
        name = deserialize_object(name, str_)
        if name == "meta":
            value = deserialize_object(value, BlockMeta)
        else:
            value = deserialize_object(value, (AttributeModel, MethodModel))
        with self.notifier.changes_squashed:
            if name in self.endpoints:
                # Stop the old Model notifying
                getattr(self, name).set_notifier_path(Model.notifier, [])
            else:
                self.call_types[name] = None
            value.set_notifier_path(self.notifier, self.path + [name])
            setattr(self, name, value)
            # Tell the notifier what changed
            self.notifier.add_squashed_change(self.path + [name], value)
            self._update_fields()
            return value

    def _update_fields(self):
        self.meta.set_fields([x for x in self.call_types if x != "meta"])

    def remove_endpoint(self, name):
        # type: (str_) -> None
        with self.notifier.changes_squashed:
            getattr(self, name).set_notifier_path(Model.notifier, [])
            self.call_types.pop(name)
            delattr(self, name)
            self._update_fields()
            self.notifier.add_squashed_change(self.path + [name])