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
        self.set_endpoint(base_string, "description", description, notify)

    def set_tags(self, tags, notify=True):
        """Set the tags list"""
        self.set_endpoint([base_string], "tags", tags, notify)
