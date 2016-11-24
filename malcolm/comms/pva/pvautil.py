import logging

import numpy as np
import pvaccess

from malcolm.compat import str_, OrderedDict


class PvaUtil(object):
    """A utility class for PvAccess conversions"""
    pva_dtypes = {
        np.int8: pvaccess.BYTE,
        np.uint8: pvaccess.UBYTE,
        np.int16: pvaccess.SHORT,
        np.uint16: pvaccess.USHORT,
        np.int32: pvaccess.INT,
        np.uint32: pvaccess.UINT,
        np.int64: pvaccess.LONG,
        np.uint64: pvaccess.ULONG,
        np.float32: pvaccess.FLOAT,
        np.float64: pvaccess.DOUBLE
    }

    def dict_to_pv_object(self, dict_in):
        pv_object = self.dict_to_pv_object_structure(dict_in)
        # Set the value of the PV object from the value dict
        logging.debug("Setting %s %s", pv_object, dict_in)
        pv_object.set(self.strip_type_id(dict_in))
        return pv_object

    def pva_type_from_value(self, value):
        if isinstance(value, str_):
            return pvaccess.STRING
        elif isinstance(value, bool):
            return pvaccess.BOOLEAN
        elif isinstance(value, np.number):
            return self.pva_dtypes[value.dtype.type]
        elif isinstance(value, np.ndarray):
            assert len(value.shape) == 1, \
                "Expected 1d array, got {}".format(value.shape)
            return [self.pva_dtypes[value.dtype.type]]
        elif isinstance(value, list):
            if len(value) == 0 or isinstance(value[0], str_):
                return [pvaccess.STRING]
            elif isinstance(value[0], bool):
                return [pvaccess.BOOLEAN]
            elif isinstance(value[0], dict):
                # variant union
                return [({},)]
        raise ValueError(
            "Cannot get pva type from %s %r" % (type(value), value))

    def dict_to_pv_object_structure(self, dict_in):
        structure = OrderedDict()
        typeid = ""
        for key, value in dict_in.items():
            if key == "typeid":
                typeid = value
                value = None
            elif isinstance(value, dict):
                value = self.dict_to_pv_object_structure(value)
            else:
                value = self.pva_type_from_value(value)
            if value is not None:
                structure[key] = value

        if structure:
            pv_object = pvaccess.PvObject(structure, typeid)
            return pv_object

    def normalize(self, value):
        # TODO: should be in pvaccess
        if isinstance(value, (np.number, np.ndarray)):
            value = value.tolist()
        return value

    def strip_type_id(self, dict_in):
        dict_out = OrderedDict()
        for key, value in dict_in.items():
            if key != "typeid":
                if isinstance(value, dict):
                    value = self.strip_type_id(value)
                value = self.normalize(value)
                if value is not None:
                    dict_out[key] = value
        if dict_out:
            return dict_out
