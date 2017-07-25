from malcolm.core import Part, method_takes, REQUIRED
from malcolm.tags import widget_types, widget, config, group
from malcolm.modules.builtin.vmetas import StringMeta, BooleanMeta, ChoiceMeta


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "widget", ChoiceMeta("Widget type", [""] + widget_types), "",
    "writeable", BooleanMeta("Is the attribute writeable?"), False,
    "group", StringMeta("If given, which GUI group should we attach to"), "",
    "config", BooleanMeta(
        "If writeable, should this field be loaded/saved?"), True)
class AttributePart(Part):
    def __init__(self, params):
        # The created attribute
        self.attr = None
        # Store params
        self.params = params
        super(AttributePart, self).__init__(params.name)

    def create_attribute_models(self):
        # Find the tags
        tags = self.create_tags()
        # Make a meta object for our attribute
        meta = self.create_meta(self.params.description, tags)
        # The attribute we will be publishing
        initial_value = self.get_initial_value()
        self.attr = meta.create_attribute_model(initial_value)
        if self.is_writeable():
            writeable_func = self.get_writeable_func()
        else:
            writeable_func = None
        yield self.params.name, self.attr, writeable_func

    def create_meta(self, description, tags):
        raise NotImplementedError()

    def is_writeable(self):
        return self.params.writeable

    def get_writeable_func(self):
        return self.attr.set_value

    def create_tags(self):
        tags = []
        if self.params.widget:
            tags.append(widget(self.params.widget))
        if self.params.config and self.is_writeable():
            # If we have a writeable func we can be a config param
            tags.append(config())
        if self.params.group:
            # If we have a group then add the tag
            tags.append(group(self.params.group))
        return tags

    def get_initial_value(self):
        """Implement this to override the attribute's initial value at creation
        """
        return None
