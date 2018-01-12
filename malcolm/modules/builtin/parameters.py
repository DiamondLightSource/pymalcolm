from annotypes import Anno, add_call_types

import numpy as np


default_desc = "Default value for parameter. If not specified, parameter is " \
               "required"

with Anno("Specify that this class will take a parameter name"):
    AName = str
with Anno("Description of this parameter"):
    ADescription = str
with Anno(default_desc):
    AStringDefault = str
with Anno(default_desc):
    AFloat64Default = np.float64
with Anno(default_desc):
    AInt32Default = np.int32
with Anno("The Anno representing the parameter"):
    AAnno = Anno


@add_call_types
def string(name, description, default=None):
    # type: (AName, ADescription, AStringDefault) -> AAnno
    """Add a string parameter to be passed when instantiating this YAML file"""
    return Anno(description, name=name, typ=str, default=default)


@add_call_types
def float64(name, description, default=None):
    # type: (AName, ADescription, AFloat64Default) -> AAnno
    """Add a float64 parameter to be passed when instantiating this YAML file"""
    return Anno(description, name=name, typ=float, default=default)


@add_call_types
def int32(name, description, default=None):
    # type: (AName, ADescription, AInt32Default) -> AAnno
    """Add an int32 parameter to be passed when instantiating this YAML file"""
    return Anno(description, name=name, typ=int, default=default)
