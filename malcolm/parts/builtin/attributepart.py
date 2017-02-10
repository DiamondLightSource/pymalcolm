from malcolm.core import Part, method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, BooleanMeta, ChoiceMeta
from malcolm.tags import widget_types, widget, config


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "widget", ChoiceMeta("Widget type", [""] + widget_types), "",
    "writeable", BooleanMeta("Is the attribute writeable?"), False,
    "config", BooleanMeta("Should this field be loaded/saved?"), False)
class AttributePart(Part):
    # Attribute instance
    attr = None

    def create_attributes(self):
        # Find the tags
        tags = self.create_tags()
        # Make a meta object for our attribute
        meta = self.create_meta(self.params.description, tags)
        # The attribute we will be publishing
        initial_value = self.get_initial_value()
        self.attr = meta.make_attribute(initial_value)
        writeable_func = self.get_writeable_func()
        yield self.params.name, self.attr, writeable_func

    def create_meta(self, description, tags):
        raise NotImplementedError()

    def get_writeable_func(self):
        if self.params.writeable:
            writeable_func = self.attr.set_value
        else:
            writeable_func = None
        return writeable_func

    def create_tags(self):
        tags = []
        if self.params.widget:
            tags.append(widget(self.params.widget))
        if self.params.config:
            tags.append(config())
        return tags

    def get_initial_value(self):
        """Implement this to override the attribute's initial value at creation
        """
        return None
