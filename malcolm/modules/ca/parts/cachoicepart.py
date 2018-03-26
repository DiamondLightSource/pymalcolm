from malcolm.compat import long_
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
        if isinstance(value, int) or isinstance(value, long_):
            # Already have the index, so validate it.
            if value < len(self.attr.meta.choices):
                pass
            else:
                raise ValueError("Provided index %d exceeds list length %d"
                                 % (value, len(self.attr.meta.choices)))
        else:
            # Validate that value is in the choices list; if so, get its index
            if value in self.attr.meta.choices:
                value = self.attr.meta.choices.index(value)
            else:
                raise ValueError("Provided value \"%s\" invalid selection from"
                                 " choices [%s]" %
                                 (value, ", ".join(self.attr.meta.choices)))
        super(CAChoicePart, self).caput(value)
