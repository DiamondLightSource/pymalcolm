from collections import OrderedDict

from malcolm.core.notifier import Notifier


class Meta(Notifier):
    """Meta base class"""

    endpoints = ["description", "tags"]

    def __init__(self, name, description, *args):
        super(Meta, self).__init__(name, *args)
        self.description = description
        self.tags = []

    def set_description(self, description, notify=True):
        self.description = description
        self.on_changed([["description"], description], notify)

    def set_tags(self, tags, notify=True):
        self.tags = tags
        self.on_changed([["tags"], tags], notify)

    @classmethod
    def from_dict(cls, name, d, *args):
        meta = cls(name, d["description"], *args)
        meta.tags = d["tags"]
        return meta
