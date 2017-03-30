import numpy as np

from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


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
        self.set_endpoint_data("dtype", dtype, notify)

    def validate(self, value):
        if value is None:
            value = 0
        cast = getattr(np, self.dtype)(value)
        return cast
