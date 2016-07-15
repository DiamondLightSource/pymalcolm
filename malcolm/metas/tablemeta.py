from collections import OrderedDict

from malcolm.core.meta import Meta
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/TableMeta:1.0")
class TableMeta(Meta):

    endpoints = ["elements", "description", "tags",
                 "writeable", "label", "headings"]

    def __init__(self, name, description):
        super(TableMeta, self).__init__(name, description)
        self.writeable = True
        self.label = ""
        self.headings = []
        self.elements = OrderedDict()

    def add_element(self, attribute_meta):
        if attribute_meta.name in self.elements:
            raise ValueError("Element already exists")
        self.elements[attribute_meta.name] = attribute_meta

    def set_writeable(self, writeable, notify=True):
        self.writeable = writeable
        self.on_changed([["writeable"], writeable], notify)

    def set_headings(self, headings, notify=True):
        self.headings = headings
        self.on_changed([["headings"], headings], notify)

    def set_label(self, label, notify=True):
        self.label = label
        self.on_changed([["label"], label], notify)

    @classmethod
    def from_dict(cls, name, d):
        table_meta = cls(name, d["description"])
        table_meta.writeable = d["writeable"]
        table_meta.tags = d["tags"]
        table_meta.label = d["label"]
        table_meta.elements = d["elements"]
        table_meta.headings = d["headings"]
        return table_meta
