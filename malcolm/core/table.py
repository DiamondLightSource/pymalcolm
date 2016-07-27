import numpy as np

from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Table:1.0")
class Table(Serializable):
    # real data stored as attributes
    # getitem supported for row by row operations

    def __init__(self, meta, d={}):
        if d is None:
            d = {}
        self.meta = meta
        for e in meta.elements:
            v = d[e] if e in d else []
            setattr(self, e, v)

    @property
    def endpoints(self):
        return [e for e in self.meta.elements]

    def verify_column_lengths(self):
        if len(self.meta.elements) == 0:
            return True
        l = len(getattr(self, list(self.meta.elements)[0]))
        for e in self.meta.elements:
            column = getattr(self, e)
            if l != len(column):
                raise AssertionError("Column lengths do not match")

    def __getitem__(self, idx):
        """Get row"""
        self.verify_column_lengths()
        columns = len(self.meta.elements)
        row = [None] * columns
        for i in range(0, columns):
            row[i] = getattr(self, list(self.meta.elements)[i])[idx]
        return row

    def __setitem__(self, idx, row):
        """Set row"""
        self.verify_column_lengths()
        if len(row) != len(self.meta.elements):
            raise ValueError(
                "Row %s does not specify correct number of values" % row)
        for e, v in zip(self.meta.elements, row):
            column = getattr(self, e)
            column[idx] = v

    def __setattr__(self, attr, value):
        """Set column"""
        if hasattr(self, "meta"):
            column_meta = self.meta.elements[attr]
            value = column_meta.validate(value)
        object.__setattr__(self, attr, value)

    def append(self, row):
        self._verify_column_lengths()
        if len(row) != len(self.meta.elements):
            raise ValueError(
                "Row %s does not specify correct number of values" % row)
        for e, v in zip(self.meta.elements, row):
            column = getattr(self, e)
            try:
                column.append(v)
            except:
                new_column = np.append(column, [v])
                setattr(self, e, new_column)

    @classmethod
    def from_dict(cls, d, meta):
        d.pop("typeid")
        t = cls(meta, d)
        return t
