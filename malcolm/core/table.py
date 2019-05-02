from annotypes import Serializable


@Serializable.register_subclass("malcolm:core/Table:1.0")
class Table(Serializable):
    # real data stored as attributes
    # getitem supported for row by row operations
    def validate_column_lengths(self):
        lengths = {a: len(getattr(self, a)) for a in self.call_types}
        assert len(set(lengths.values())) == 1, \
            "Column lengths %s don't match" % lengths

    def __getitem__(self, item):
        try:
            return super(Table, self).__getitem__(item)
        except KeyError:
            # If we have an integer, make a row
            if isinstance(item, int):
                self.validate_column_lengths()
                return [getattr(self, a)[item] for a in self.call_types]
            else:
                raise

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

    def __eq__(self, other):
        # type: (object) -> bool
        return not self != other

    def __ne__(self, other):
        if not isinstance(other, Table):
            return True
        if list(self.call_types) != list(other.call_types):
            return True
        for k in self.call_types:
            if self[k] != other[k]:
                return True
        return False
