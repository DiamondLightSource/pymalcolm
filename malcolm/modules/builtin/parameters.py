from annotypes import Anno, add_call_types


default_desc = "Default value for parameter. If not specified, parameter is " \
               "required"

with Anno("Specify that this class will take a parameter name"):
    AName = str
with Anno("Description of this parameter"):
    ADescription = str
with Anno(default_desc):
    AStringDefault = str
with Anno(default_desc):
    AFloat64Default = float
with Anno(default_desc):
    AInt32Default = int
with Anno("The Anno representing the parameter"):
    AAnno = Anno


def common_args(name, default):
    for s in name.split("_"):
        # Only support UPP3R or l0wer case for each _ section
        assert s.islower() or s.isupper(), \
            "Parameter %s should be snake_case" % (name,)
    ret = dict(name=name)
    if default is not None:
        ret["default"] = default
    return ret


@add_call_types
def string(name, description, default=None):
    # type: (AName, ADescription, AStringDefault) -> AAnno
    """Add a string parameter to be passed when instantiating this YAML file"""
    args = common_args(name, default)
    return Anno(description, **args).set_typ(str)


@add_call_types
def float64(name, description, default=None):
    # type: (AName, ADescription, AFloat64Default) -> AAnno
    """Add a float64 parameter to be passed when instantiating this YAML file"""
    args = common_args(name, default)
    return Anno(description, **args).set_typ(float)


@add_call_types
def int32(name, description, default=None):
    # type: (AName, ADescription, AInt32Default) -> AAnno
    """Add an int32 parameter to be passed when instantiating this YAML file"""
    args = common_args(name, default)
    return Anno(description, **args).set_typ(int)
