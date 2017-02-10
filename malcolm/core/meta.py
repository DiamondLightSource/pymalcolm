from malcolm.compat import str_
from malcolm.core.monitorable import Monitorable
from malcolm.core.serializable import deserialize_object
from malcolm.core.stringarray import StringArray


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
        # List of state names that we are writeable in
        self.writeable_in = []

    def set_description(self, description, notify=True):
        """Set the description string"""
        description = deserialize_object(description, str_)
        self.set_endpoint_data("description", description, notify)

    def set_tags(self, tags, notify=True):
        """Set the tags list"""
        tags = StringArray(deserialize_object(t, str_) for t in tags)
        self.set_endpoint_data("tags", tags, notify)

    def set_writeable(self, writeable, notify=True):
        """Set the writeable bool"""
        writeable = deserialize_object(writeable, bool)
        self.set_endpoint_data("writeable", writeable, notify)

    def set_label(self, label, notify=True):
        """Set the label string"""
        label = deserialize_object(label, str_)
        self.set_endpoint_data("label", label, notify)

    def set_writeable_in(self, *states):
        self.writeable_in = states
