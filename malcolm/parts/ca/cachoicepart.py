from malcolm.core.vmetas import ChoiceMeta
from malcolm.parts.ca.capart import CAPart


class CAChoicePart(CAPart):
    """Defines a part which connects to a pv via channel access DBR_ENUM"""

    def create_meta(self, description, tags):
        return ChoiceMeta(description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_ENUM

    def set_initial_value(self, value):
        self.attr.meta.set_choices(value.enums)
        super(CAChoicePart, self).set_initial_value(value)

    def caput(self, value):
        try:
            value = self.attr.meta.choices.index(value)
        except ValueError:
            # Already have the index
            pass
        super(CAChoicePart, self).caput(value)
