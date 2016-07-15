from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Table:1.0")
class Table(Serializable):

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

    def _verify_column_lengths(self):
        if len(self.meta.elements) == 0:
            return True
        l = len(getattr(self, list(self.meta.elements)[0]))
        for e in self.meta.elements:
            column = getattr(self, e)
            if l != len(column):
                raise AssertionError("Column lengths do not match")

    def __getitem__(self, idx):
        self._verify_column_lengths()
        columns = len(self.meta.elements)
        row = [None] * columns
        for i in range(0, columns):
            row[i] = getattr(self, list(self.meta.elements)[i])[idx]
        return row

    def __setitem__(self, idx, row):
        self._verify_column_lengths()
        if len(row) != len(self.meta.elements):
            raise ValueError(
                "Row %s does not specify correct number of values" % row)
        for e, v in zip(self.meta.elements, row):
            column = getattr(self, e)
            column[idx] = v

    def append(self, row):
        self._verify_column_lengths()
        if len(row) != len(self.meta.elements):
            raise ValueError(
                "Row %s does not specify correct number of values" % row)
        for e, v in zip(self.meta.elements, row):
            column = getattr(self, e)
            column.append(v)

    @classmethod
    def from_dict(cls, meta, d):
        if "typeid" in d:
            d = d.copy()
            del d["typeid"]
        t = cls(meta, d)
        return t
