import numpy

from malcolm.metas.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable
from malcolm.compat import base_string


@Serializable.register_subclass("malcolm:core/NumberArrayMeta:1.0")
class NumberArrayMeta(ScalarMeta):
    """Meta object containing information for an array of numerical values"""

    endpoints = ["dtype", "description", "tags", "writeable", "label"]

    def __init__(self, name, description, dtype):
        super(NumberArrayMeta, self).__init__(name, description)
        self.dtype = dtype

    def validate(self, value):

        if value is None:
            return None

        elif type(value) == list:
            casted_array = numpy.array(value, dtype=self.dtype)
            for i, number in enumerate(value):
                if number is None:
                    raise ValueError("Array elements cannot be null")
                if not isinstance(number, base_string):
                    cast = casted_array[i]
                    if not numpy.isclose(cast, number):
                        raise ValueError("Lost information converting %s to %s"
                                         % (value, cast))
            return casted_array

        else:
            if not hasattr(value, 'dtype'):
                raise TypeError("Expected numpy array or list, got %s"
                                % type(value))
            if value.dtype != numpy.dtype(self.dtype()):
                raise TypeError("Expected %s, got %s" %
                                (numpy.dtype(self.dtype()), value.dtype))
            return value

    def to_dict(self):
        return super(NumberArrayMeta, self).to_dict(
            dtype=self.dtype().dtype.name)

    @classmethod
    def from_dict(cls, name, d):
        dtype = numpy.dtype(d["dtype"])
        meta = cls(name, d["description"], dtype)
        meta.writeable = d["writeable"]
        meta.tags = d["tags"]
        meta.label = d["label"]
        return meta
