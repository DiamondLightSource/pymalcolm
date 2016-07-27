from malcolm.core.notifier import Notifier
from malcolm.compat import base_string


class Meta(Notifier):
    """Meta base class"""

    endpoints = ["description", "tags"]

    def __init__(self, description="", tags=None):
        self.set_description(description)
        if tags is None:
            tags = []
        self.set_tags(tags)

    def set_description(self, description, notify=True):
        """Set the description string"""
        assert isinstance(description, base_string), \
            "Expected description to be a string, got %s" % (description,)
        self.set_endpoint("description", description, notify)

    def set_tags(self, tags, notify=True):
        """Set the tags list"""
        assert isinstance(tags, list), \
            "Expected tags to be a list, got %s" % (tags,)
        for tag in tags:
            assert isinstance(tag, base_string), \
                "Expected tag to be string, got %s" % (tag,)
        self.set_endpoint("tags", tags, notify)
