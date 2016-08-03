from malcolm.core.monitorable import Monitorable
from malcolm.compat import base_string


class Meta(Monitorable):
    """Meta base class"""

    endpoints = ["description", "tags", "writeable", "label"]

    def __init__(self, description="", tags=None, writeable=False, label=""):
        self.set_description(description)
        if tags is None:
            tags = []
        self.set_tags(tags)
        self.set_writeable(writeable)
        self.set_label(label)

    def set_description(self, description, notify=True):
        """Set the description string"""
        self.set_endpoint(base_string, "description", description, notify)

    def set_tags(self, tags, notify=True):
        """Set the tags list"""
        self.set_endpoint([base_string], "tags", tags, notify)

    def set_writeable(self, writeable, notify=True):
        """Set the writeable bool"""
        self.set_endpoint(bool, "writeable", writeable, notify)

    def set_label(self, label, notify=True):
        """Set the label string"""
        self.set_endpoint(base_string, "label", label, notify)
