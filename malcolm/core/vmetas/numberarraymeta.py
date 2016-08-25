import numpy as np

from malcolm.compat import str_
from malcolm.core.serializable import Serializable
from malcolm.core.varraymeta import VArrayMeta
from malcolm.core.vmetas.numbermeta import NumberMeta


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
                if not isinstance(number, str_):
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