import numpy as np

from malcolm.core.serializable import Serializable
from malcolm.core.varraymeta import VArrayMeta
from malcolm.core.vmetas.numberarraymeta import validate_array


@Serializable.register_subclass("malcolm:core/BooleanArrayMeta:1.0")
class BooleanArrayMeta(VArrayMeta):
    """Meta object containing information for a boolean array"""

    def validate(self, value):
        return validate_array(value, np.bool_)
