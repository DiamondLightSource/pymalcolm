from collections import OrderedDict

import numpy

from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable
from malcolm.compat import base_string


@Serializable.register("malcolm:core/NumberArrayMeta:1.0")
class NumberArrayMeta(ScalarMeta):
    """Meta object containing information for an array of numerical values"""

    def __init__(self, name, description, dtype_list):
        super(NumberArrayMeta, self).__init__(name, description)
        self.dtype_list = dtype_list

    def validate(self, value):
        if value is None:
            return None

        casted_array = []
        for i, number in enumerate(value):
            if number is None:
                raise ValueError("Array elements can not be null")
            cast = self.dtype_list[i](number)
            if not isinstance(number, base_string):
                assert cast == number, \
                    "Lost information converting %s to %s" % (number, cast)
            casted_array.append(cast)

        return casted_array

    def to_dict(self):
        d = OrderedDict()
        d["typeid"] = self.typeid
        d["dtype_list"] = [dtype().dtype.name for dtype in self.dtype_list]

        d.update(super(NumberArrayMeta, self).to_dict())
        return d

    @classmethod
    def from_dict(cls, name, d):
        dtype_list = [numpy.dtype(dtype).type for dtype in d["dtype_list"]]
        meta = cls(name, d["description"], dtype_list)
        meta.writeable = d["writeable"]
        meta.tags = d["tags"]
        meta.label = d["label"]
        return meta
