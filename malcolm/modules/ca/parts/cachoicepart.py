from malcolm.modules.builtin.vmetas import ChoiceMeta
from .capart import CAPart


class CAChoicePart(CAPart):
    """Defines a string `Attribute` that talks to a DBR_ENUM mbbo PV"""

    def create_meta(self, description, tags):
        return ChoiceMeta(description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_ENUM

    def set_initial_metadata(self, value):
        self.attr.meta.set_choices(value.enums)

    def caput(self, value):
        try:
            value = self.attr.meta.choices.index(value)
        except ValueError:
            # Already have the index
            pass
        super(CAChoicePart, self).caput(value)
