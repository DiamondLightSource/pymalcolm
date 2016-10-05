from cothread import catools

from malcolm.core.vmetas import ChoiceMeta
from malcolm.parts.ca.capart import CAPart, capart_takes


@capart_takes()
class CAChoicePart(CAPart):
    """Defines a part which connects to a pv via channel access DBR_ENUM"""

    def create_meta(self, description, tags):
        return ChoiceMeta(description=description, tags=tags)

    def get_datatype(self):
        return catools.DBR_ENUM

    def update_value(self, value):
        if hasattr(value, 'enums') and value.ok:
            self.attr.meta.set_choices(value.enums)
        super(CAChoicePart, self).update_value(value)

    def caput(self, value):
        try:
            value = self.attr.meta.choices.index(value)
        except ValueError:
            # Already have the index
            pass
        super(CAChoicePart, self).caput(value)
