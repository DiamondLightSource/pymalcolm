import numpy as np

from malcolm.core import Serializable, VMeta


@Serializable.register_subclass("malcolm:core/NumberMeta:1.0")
class NumberMeta(VMeta):
    """Meta object containing information for a numerical value"""

    endpoints = ["dtype", "description", "tags", "writeable", "label"]
    _dtypes = ["int8", "uint8", "int16", "uint16", "int32", "uint32", "int64",
               "uint64", "float32", "float64"]

    def __init__(self, dtype="float64", description="", tags=(),
                 writeable=False, label=""):
        super(NumberMeta, self).__init__(description, tags, writeable, label)
        # like np.float64
        self._np_dtype = None
        # like "float64"
        self.dtype = self.set_dtype(dtype)

    def set_dtype(self, dtype):
        """Set the dtype string"""
        assert dtype in self._dtypes, \
            "Expected dtype to be in %s, got %s" % (self._dtypes, dtype)
        self._np_dtype = getattr(np, dtype)
        return self.set_endpoint_data("dtype", dtype)

    def validate(self, value):
        if value is None:
            value = 0
        cast = self._np_dtype(value)
        return cast

    def doc_type_string(self):
        return "%s" % self.dtype
