from malcolm.core import Part, method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, BooleanMeta


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "widget", StringMeta("Widget, like 'combo' or 'textinput'"), "",
    "writeable", BooleanMeta("Is the attribute writeable?"), "",
    "initialValue", StringMeta("Initial value of attribute"), "",
)
class StringPart(Part):
    # Attribute instance
    attr = None

    def create_attributes(self):
        # The attribute we will be publishing
        self.attr = self.create_meta().make_attribute(self.params.initialValue)
        if self.params.writeable:
            writeable_func = self.attr.set_value
        else:
            writeable_func = None
        yield self.params.name, self.attr, writeable_func

    def create_tags(self):
        tags = []
        if self.params.widget:
            assert ":" not in self.params.widget, \
                "Widget tag %r should not specify 'widget:' prefix" \
                % self.params.widget
            tags.append("widget:%s" % self.params.widget)
        return tags

    def create_meta(self):
        meta = StringMeta(description=self.params.description,
                          tags=self.create_tags())
        return meta
