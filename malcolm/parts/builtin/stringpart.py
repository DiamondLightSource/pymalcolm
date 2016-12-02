from malcolm.core import Part, method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, BooleanMeta, ChoiceMeta
from malcolm.tags import widget_types, widget


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "widget", ChoiceMeta("Widget type", [""] + widget_types), "",
    "writeable", BooleanMeta("Is the attribute writeable?"), False,
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
            tags.append(widget(self.params.widget))
        return tags

    def create_meta(self):
        meta = StringMeta(description=self.params.description,
                          tags=self.create_tags())
        return meta
