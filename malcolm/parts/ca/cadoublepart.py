import numpy as np
from cothread import catools

from malcolm.parts.ca.capart import CAPart
from malcolm.metas.numbermeta import NumberMeta
from malcolm.metas.stringmeta import StringMeta
from malcolm.core.method import takes, returns, REQUIRED


class CADoublePart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_DOUBLE"""

    @takes(
        StringMeta("name", "name of created attribute"), REQUIRED,
        StringMeta("description", "desc of created attribute"), REQUIRED,
        StringMeta("pv", "full pv of demand and default for rbv"), None,
        StringMeta("rbv", "override for rbv"), None,
        StringMeta("rbv_suff", "set rbv ro pv + rbv_suff"), None,
    )
    def setup(self, params):
        """ setup is called by the base class Part.__init__ via self.Method.
            self.Method is defined by the @takes decorator above.
            It defines an attribute to publish the pv

        Args:
            params(Map): parameters described in @takes
        """
        meta = NumberMeta("meta", params.description, np.float64)
        self.create_attribute(meta, params.pv, rbv=params.rbv,
                              rbv_suff=params.rbv_suff)


    def get_datatype(self):
        return catools.DBR_DOUBLE