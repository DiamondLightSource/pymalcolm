from malcolm.compat import str_
from .model import Model
from .serializable import deserialize_object
from .stringarray import StringArray


class Meta(Model):
    """Meta base class"""

    endpoints = ["description", "tags", "writeable", "label"]

    def __init__(self, description="", tags=(), writeable=False, label=""):
        # Set initial values
        self.description = self.set_description(description)
        self.tags = self.set_tags(tags)
        self.writeable = self.set_writeable(writeable)
        self.label = self.set_label(label)
        # List of state names that we are writeable in, not serializable
        self.writeable_in = []

    def set_description(self, description):
        """Set the description string"""
        description = deserialize_object(description, str_)
        return self.set_endpoint_data("description", description)

    def set_tags(self, tags):
        """Set the tags StringArray"""
        tags = StringArray(deserialize_object(t, str_) for t in tags)
        return self.set_endpoint_data("tags", tags)

    def set_writeable(self, writeable):
        """Set the writeable bool"""
        writeable = deserialize_object(writeable, bool)
        return self.set_endpoint_data("writeable", writeable)

    def set_label(self, label):
        """Set the label string"""
        label = deserialize_object(label, str_)
        return self.set_endpoint_data("label", label)

    def set_writeable_in(self, *states):
        """Set the states that the object is writeable in"""
        states = tuple(deserialize_object(state, str_) for state in states)
        self.writeable_in = states
