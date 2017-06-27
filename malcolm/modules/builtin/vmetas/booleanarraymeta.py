import numpy as np

from malcolm.core import Serializable, VArrayMeta
from .numberarraymeta import validate_array


@Serializable.register_subclass("malcolm:core/BooleanArrayMeta:1.0")
class BooleanArrayMeta(VArrayMeta):
    """Meta object containing information for a boolean array"""

    def validate(self, value):
        """Cast value to boolean array and return it

        Args:
            value: Value to validate

        Returns:
            `numpy.ndarray` Value as a boolean numpy array
        """
        return validate_array(value, np.bool_)

    def doc_type_string(self):
        return "[bool]"
