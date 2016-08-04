from collections import OrderedDict

import numpy as np
from scanpointgenerator import CompoundGenerator

from malcolm.core.serializable import Serializable
from malcolm.core.monitorable import NO_VALIDATE
from malcolm.core.map import Map
from malcolm.core.table import Table
from malcolm.core.meta import Meta
from malcolm.compat import base_string


class VMeta(Meta):
    """Abstract base class for Validating Meta objects"""

    def validate(self, value):
        """
        Abstract function to validate a given value

        Args:
            value(abstract): Value to validate
        """
        raise NotImplementedError(
            "Abstract validate function must be implemented in child classes")


class VArrayMeta(VMeta):
    # intermediate class so TableMeta can say "only arrays"
    pass


@Serializable.register_subclass("malcolm:core/BooleanArrayMeta:1.0")
class BooleanArrayMeta(VArrayMeta):
    """Meta object containing information for a boolean array"""

    def validate(self, value):
        """
        Verify value can be iterated and cast elements to boolean

        Args:
            value (iterable): value to be validated

        Returns:
            List of Booleans or None if value is None
        """
        if value is None:
            return None
        if not hasattr(value, "__iter__"):
            raise ValueError("%s is not iterable" % value)
        validated = [bool(x) if x is not None else None for x in value]
        if None in validated:
            raise ValueError("Array elements can not be null")
        return validated


@Serializable.register_subclass("malcolm:core/BooleanMeta:1.0")
class BooleanMeta(VMeta):
    """Meta object containing information for a boolean"""

    def validate(self, value):
        """
        Check if the value is None and returns None, else casts value to a
        boolean and returns it

        Args:
            value: Value to validate

        Returns:
            bool: Value as a boolean [If value is not None]
        """

        if value is None:
            return None
        else:
            return bool(value)


@Serializable.register_subclass("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(VMeta):
    """Meta object containing information for a enum"""

    endpoints = ["description", "choices", "tags", "writeable", "label"]

    def __init__(self, description="", choices=None, tags=None, writeable=False,
                 label=""):
        super(ChoiceMeta, self).__init__(description, tags, writeable, label)
        if choices is None:
            choices = []
        self.set_choices(choices)

    def set_choices(self, choices, notify=True):
        """Set the choices list"""
        self.set_endpoint([base_string], "choices", choices, notify)

    def validate(self, value):
        """
        Check if the value is valid returns it

        Args:
            value: Value to validate

        Returns:
            Value if it is valid
        Raises:
            ValueError: If value not valid
        """
        if value is None or value in self.choices:
            return value
        elif isinstance(value, int) and value < len(self.choices):
            return value
        else:
            raise ValueError(
                "%s is not a valid value in %s" % (value, self.choices))


@Serializable.register_subclass("malcolm:core/ChoiceArrayMeta:1.0")
class ChoiceArrayMeta(ChoiceMeta, VArrayMeta):
    """Meta object containing information for a choice array"""

    def validate(self, value):
        """
        Verify value can be iterated and cast elements to choices

        Args:
            value(iterable): Value to be validated

        Returns:
            List of Choices or None if value is None
        """

        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueError("%r is not a list" % (value,))

        for i, choice in enumerate(value):
            if choice is None:
                raise ValueError("Array elements can not be null")
            if choice not in self.choices:
                raise ValueError("%s is not a valid value for element %s" %
                                 (choice, i))

        return value


@Serializable.register_subclass("malcolm:core/NumberMeta:1.0")
class NumberMeta(VMeta):
    """Meta object containing information for a numerical value"""

    endpoints = ["dtype", "description", "tags", "writeable", "label"]
    _dtypes = ["int8", "uint8", "int16", "uint16", "int32", "uint32", "int64",
               "uint64", "float32", "float64"]

    def __init__(self, dtype="float64", description="", tags=None,
                 writeable=False, label=""):
        super(NumberMeta, self).__init__(description, tags, writeable, label)
        # like "float64"
        self.set_dtype(dtype)

    def set_dtype(self, dtype, notify=True):
        """Set the dtype string"""
        assert dtype in self._dtypes, \
            "Expected dtype to be in %s, got %s" % (self._dtypes, dtype)
        self.set_endpoint(NO_VALIDATE, "dtype", dtype, notify)

    def validate(self, value):
        if value is None:
            return None
        cast = getattr(np, self.dtype)(value)
        if not isinstance(value, base_string):
            if not np.isclose(cast, value):
                raise ValueError("Lost information converting %s to %s"
                                 % (value, cast))
        return cast


@Serializable.register_subclass("malcolm:core/NumberArrayMeta:1.0")
class NumberArrayMeta(NumberMeta, VArrayMeta):
    """Meta object containing information for an array of numerical values"""

    def validate(self, value):

        if value is None:
            return None

        elif type(value) == list:
            casted_array = np.array(value, dtype=self.dtype)
            for i, number in enumerate(value):
                if number is None:
                    raise ValueError("Array elements cannot be null")
                if not isinstance(number, base_string):
                    cast = casted_array[i]
                    if not np.isclose(cast, number):
                        raise ValueError("Lost information converting %s to %s"
                                         % (value, cast))
            return casted_array

        else:
            if not hasattr(value, 'dtype'):
                raise TypeError("Expected numpy array or list, got %s"
                                % type(value))
            if value.dtype != np.dtype(self.dtype):
                raise TypeError("Expected %s, got %s" %
                                (np.dtype(self.dtype), value.dtype))
            return value


@Serializable.register_subclass("malcolm:core/PointGeneratorMeta:1.0")
class PointGeneratorMeta(VMeta):

    def validate(self, value):
        if value is None or isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, (OrderedDict, dict)):
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError(
                "Value %s must be a Generator object or dictionary" % value)


@Serializable.register_subclass("malcolm:core/StringArrayMeta:1.0")
class StringArrayMeta(VArrayMeta):
    """Meta object containing information for a string array"""

    def validate(self, value):
        """
        Verify value can be iterated and cast elements to strings

        Args:
            value (iterable): value to be validated

        Returns:
            List of Strings or None if value is None
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueError("%r is not a list" % (value,))

        validated = [str(x) if x is not None else None for x in value]

        if None in validated:
            raise ValueError("Array elements can not be null")

        return validated


@Serializable.register_subclass("malcolm:core/StringMeta:1.0")
class StringMeta(VMeta):
    """Meta object containing information for a string"""

    def validate(self, value):
        """
        Check if the value is None and returns None, else casts value to a
        string and returns it

        Args:
            value: Value to validate

        Returns:
            str: Value as a string [If value is not None]
        """

        if value is None:
            return None
        else:
            return str(value)


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(VMeta):

    endpoints = ["elements", "description", "tags",
                 "writeable", "label", "headings"]

    def __init__(self, description="", tags=None, writeable=False, label=""):
        super(TableMeta, self).__init__(description, tags, writeable, label)
        self.set_headings([])
        self.elements = OrderedDict()

    def set_elements(self, elements, notify=True):
        """Set the elements dict from a ScalarArrayMeta or serialized dict"""
        emap = Map()
        for k, v in elements.items():
            assert isinstance(k, base_string), "Expected string, got %s" % (k,)
            if k != "typeid":
                emap[k] = self._cast(v, VArrayMeta)
        self.set_endpoint(NO_VALIDATE, "elements", emap, notify)

    def set_headings(self, headings, notify=True):
        """Set the headings list"""
        self.set_endpoint([base_string], "headings", headings, notify)

    def validate(self, value):
        if not isinstance(value, Table):
            # turn it into a table
            value = Table.from_dict(value, meta=self)
        else:
            # Check that it's using the same meta object
            assert self == value.meta, \
                "Supplied table with wrong meta type"
        # Check column lengths
        value.verify_column_lengths()
        return value

