from collections import OrderedDict

from malcolm.core.attribute import Attribute
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("epics:nt/NTTable:1.0")
class NTTable(Attribute):
    def to_dict(self):
        d = OrderedDict()
        d["typeid"] = self.typeid
        # Add labels for compatibility with epics normative types
        labels = []
        for column_name in self.meta.elements:
            column_meta = self.meta.elements[column_name]
            if column_meta.label:
                labels.append(column_meta.label)
            else:
                labels.append(column_name)
        d["labels"] = labels
        d.update(super(NTTable, self).to_dict())
        return d

    @classmethod
    def from_dict(cls, d):
        d.pop("labels")
        return super(NTTable, cls).from_dict(d)