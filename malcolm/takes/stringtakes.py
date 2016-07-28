from malcolm.takes.takes import Takes, name_and_description
from malcolm.metas import StringMeta
from malcolm.core.method import takes, OPTIONAL
from malcolm.compat import base_string


@takes(*name_and_description + [
    StringMeta("default", "Default string value for parameter. If not " +
               "specified, parameter is required"), OPTIONAL
])
class StringTakes(Takes):
    def set_default(self, default):
        assert isinstance(default, base_string), \
            "Expected string, got %s" % (default,)
        self.default = default

    def make_meta(self):
        return StringMeta(self.name, self.description)
