import numpy as np

from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Table:1.0")
class Table(Serializable):
    # real data stored as attributes
    # getitem supported for row by row operations

    def __init__(self, meta, d=None):
        self.meta = meta
        if d is None:
            d = {}
        for e in meta.elements:
            v = d[e] if e in d else []
            setattr(self, e, v)

    @property
    def endpoints(self):
        return list(self.meta.elements)

    def verify_column_lengths(self):
        if len(self.meta.elements) == 0:
            return True
        lengths = [len(getattr(self, e)) for e in self.meta.elements]
        assert len(set(lengths)) == 1, \
            "Column lengths %s don't match" % lengths

    def __getitem__(self, idx):
        """Get row"""
        if isinstance(idx, int):
            self.verify_column_lengths()
            columns = len(self.meta.elements)
            row = [None] * columns
            for i in range(columns):
                row[i] = getattr(self, list(self.meta.elements)[i])[idx]
            return row
        else:
            return getattr(self, idx)

    def __setitem__(self, idx, row):
        """Set row for int, column for string"""
        if isinstance(idx, int):
            # set row
            self.verify_column_lengths()
            if len(row) != len(self.meta.elements):
                raise ValueError(
                    "Row %s does not specify correct number of values" % row)
            for e, v in zip(self.meta.elements, row):
                column = getattr(self, e)
                column[idx] = v
        else:
            setattr(self, idx, row)

    def __setattr__(self, attr, value):
        """Set column"""
        if hasattr(self, "meta") and attr in self.meta.elements:
            column_meta = self.meta.elements[attr]
            value = column_meta.validate(value)
            self.set_endpoint_data(attr, value)
        else:
            object.__setattr__(self, attr, value)

    def append(self, row):
        self.verify_column_lengths()
        if len(row) != len(self.meta.elements):
            raise ValueError(
                "Row %s does not specify correct number of values" % row)
        for e, v in zip(self.meta.elements, row):
            column = getattr(self, e)
            try:
                column.append(v)
            except AttributeError:
                # numpy arrays have no append, so make an array of the right
                # validated type, and use np.append
                v = self.meta.elements[e].validate([v])
                new_column = np.append(column, v)
                setattr(self, e, new_column)

