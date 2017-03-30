import numpy as np

from malcolm.core.serializable import Serializable
from malcolm.core.varraymeta import VArrayMeta
from malcolm.core.vmetas.numbermeta import NumberMeta


def validate_array(value, dtype):
    if value is None:
        # Make an empty array
        cast = np.array([], dtype=dtype)
    elif type(value) == list:
        # Cast to numpy array
        cast = np.array(value, dtype=dtype)
    else:
        # Check we are given a numpy array
        if not hasattr(value, 'dtype'):
            raise TypeError("Expected numpy array or list, got %s"
                            % type(value))
        if value.dtype != np.dtype(dtype):
            raise TypeError("Expected %s, got %s" %
                            (np.dtype(dtype), value.dtype))
        cast = value
    cast.setflags(write=False)
    return cast


@Serializable.register_subclass("malcolm:core/NumberArrayMeta:1.0")
class NumberArrayMeta(NumberMeta, VArrayMeta):
    """Meta object containing information for an array of numerical values"""
    def validate(self, value):
        return validate_array(value, self.dtype)
