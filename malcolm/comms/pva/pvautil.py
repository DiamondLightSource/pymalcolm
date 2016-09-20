from collections import OrderedDict
import pvaccess
from malcolm.compat import long_

class PvaUtil(object):
    """A utility class for PvAccess conversions"""

    def dict_to_pv_object(self, dict_in):
        pv_object = self.dict_to_pv_object_structure(dict_in)
        # Set the value of the PV object from the value dict
        pv_object.set(self.strip_type_id(dict_in))
        return pv_object

    def dict_to_pv_object_structure(self, dict_in):
        structure = OrderedDict()
        typeid = None
        for item in dict_in:
            if item == "typeid":
                typeid = dict_in[item]
            else:
                if isinstance(dict_in[item], str):
                    structure[item] = pvaccess.STRING
                elif isinstance(dict_in[item], bool):
                    structure[item] = pvaccess.BOOLEAN
                elif isinstance(dict_in[item], float):
                    structure[item] = pvaccess.FLOAT
                elif isinstance(dict_in[item], int):
                    structure[item] = pvaccess.INT
                elif isinstance(dict_in[item], long_):
                    structure[item] = pvaccess.LONG
                elif isinstance(dict_in[item], list):
                    # self.log_debug("List found: %s", item)
                    if not dict_in[item]:
                        structure[item] = [pvaccess.STRING]
                    else:
                        if isinstance(dict_in[item][0], str):
                            structure[item] = [pvaccess.STRING]
                        elif isinstance(dict_in[item][0], bool):
                            structure[item] = [pvaccess.BOOLEAN]
                        elif isinstance(dict_in[item][0], float):
                            structure[item] = [pvaccess.FLOAT]
                        elif isinstance(dict_in[item][0], int):
                            structure[item] = [pvaccess.INT]
                        elif isinstance(dict_in[item][0], long_):
                            structure[item] = [pvaccess.LONG]
                        elif isinstance(dict_in[item][0], OrderedDict):
                            structure[item] = [({},)]
                elif isinstance(dict_in[item], OrderedDict):
                    dict_structure = self.dict_to_pv_object_structure(dict_in[item])
                    if dict_structure:
                        structure[item] = dict_structure

        try:
            if not structure:
                return None

            if not typeid:
                pv_object = pvaccess.PvObject(structure, "")
            else:

                pv_object = pvaccess.PvObject(structure, typeid)
        except:
            self.log_error("Unable to create PvObject structure from OrderedDict")
            raise

        return pv_object

    def strip_type_id(self, dict_in):
        dict_out = OrderedDict()
        for item in dict_in:
            if item != "typeid":
                if isinstance(dict_in[item], OrderedDict):
                    dict_values = self.strip_type_id(dict_in[item])
                    if dict_values:
                        dict_out[item] = dict_values
                else:
                    dict_out[item] = dict_in[item]
        return dict_out
