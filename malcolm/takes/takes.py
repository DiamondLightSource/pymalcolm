from malcolm.core.serializable import Serializable
from malcolm.core.method import REQUIRED
from malcolm.compat import base_string
from malcolm.metas import StringMeta


# Don't decorate with @takes because we shouldn't be able to deserialize this...
name_and_description = [
    StringMeta("name", "Specify that this class will take a parameter name"),
    REQUIRED,
    StringMeta("description", "Description of this parameter"),
    REQUIRED,
]


class Takes(Serializable):

    @property
    def endpoints(self):
        # default should only be there if someone as called set_default
        endpoints = ["name", "description"]
        if self.default is not REQUIRED:
            endpoints.append("default")
        return endpoints

    def __init__(self, name="", description=""):
        self.set_name(name)
        self.set_description(description)
        self.default = REQUIRED

    def set_name(self, name):
        assert isinstance(name, base_string), \
            "Needed string, got %r" (name,)
        self.name = name

    def set_description(self, description):
        assert isinstance(description, base_string), \
            "Needed string, got %r" (description,)
        self.description = description

    def set_default(self, default):
        raise NotImplementedError()

    def make_meta(self):
        raise NotImplementedError()
