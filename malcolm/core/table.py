from .serializable import Serializable


@Serializable.register_subclass("malcolm:core/Table:1.0")
class Table(Serializable):
    # real data stored as attributes
    # getitem supported for row by row operations
    def validate_column_lengths(self):
        lengths = {a: len(getattr(self, a)) for a in self.call_types}
        assert len(set(lengths.values())) == 1, \
            "Column lengths %s don't match" % lengths

    def __getitem__(self, item):
        if isinstance(item, int):
            self.validate_column_lengths()
            return [getattr(self, a)[item] for a in self.call_types]
        else:
            return super(Table, self).__getitem__(item)

    @classmethod
    def from_rows(cls, rows):
        attrs = {k: [] for k in cls.call_types}
        for row in rows:
            for key, data in zip(cls.call_types, row):
                attrs[key].append(data)
        attrs = {k: cls.call_types[k](v) for k, v in attrs.items()}
        return cls(**attrs)

    def rows(self):
        self.validate_column_lengths()
        data = [getattr(self, a) for a in self.call_types]
        for row in zip(*data):
            yield list(row)
