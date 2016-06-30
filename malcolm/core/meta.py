from collections import OrderedDict

from malcolm.core.serializable import Serializable


@Serializable.register("malcolm:core/Meta:1.0")
class Meta(Serializable):
    """Meta class for describing Blocks"""

    def __init__(self, name, description):
        super(Meta, self).__init__(name)
        self.description = description
        self.tags = []

    def update(self, change):
        """Update meta state

        Args:
            change [[element], new_value]: change to make to meta
        """
        if len(change[0]) != 1:
            raise ValueError(
                "Change %s specifies substructure that can not exist in Meta"
                % change)
        if change[0][0] == "description":
            self.set_description(change[1], notify=True)
        elif change[0][0] == "tags":
            self.set_tags(change[1], notify=True)
        else:
            raise ValueError(
                "Change %s refers to unknown meta attribute" % change)

    def set_description(self, description, notify=True):
        self.description = description
        self.on_changed([["description"], description], notify)

    def set_tags(self, tags, notify=True):
        self.tags = tags
        self.on_changed([["tags"], tags], notify)

    def to_dict(self):
        d = OrderedDict()
        d["description"] = self.description
        d["tags"] = self.tags
        d["typeid"] = self.typeid
        return d

    @classmethod
    def from_dict(cls, name, d):
        meta = Meta(name, d["description"])
        meta.tags = d["tags"]
        return meta
