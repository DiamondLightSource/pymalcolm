from malcolm.core import method_takes, REQUIRED, OPTIONAL
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta


def args_for_takes(params, meta_cls, *meta_args):
    meta_args += (params.description,)
    meta = meta_cls(*meta_args)
    if hasattr(params, "default"):
        return [params.name, meta, params.default]
    else:
        return [params.name, meta, REQUIRED]


default_desc = "Default value for parameter. If not specified, parameter is " \
               "required"

@method_takes(
    "name", StringMeta(
        "Specify that this class will take a parameter name"), REQUIRED,
    "description", StringMeta(
        "Description of this parameter"), REQUIRED,
    "default", StringMeta(default_desc), OPTIONAL)
def string(params):
    """Add a string parameter to be passed when instantiating this YAML file"""
    return args_for_takes(params, StringMeta)


@method_takes(
    "name", StringMeta(
        "Specify that this class will take a parameter name"), REQUIRED,
    "description", StringMeta(
        "Description of this parameter"), REQUIRED,
    "default", NumberMeta("float64", default_desc), OPTIONAL)
def float64(params):
    """Add a float64 parameter to be passed when instantiating this YAML file"""
    return args_for_takes(params, NumberMeta, "float64")


@method_takes(
    "name", StringMeta(
        "Specify that this class will take a parameter name"), REQUIRED,
    "description", StringMeta(
        "Description of this parameter"), REQUIRED,
    "default", NumberMeta("int32", default_desc), OPTIONAL)
def int32(params):
    """Add an int32 parameter to be passed when instantiating this YAML file"""
    return args_for_takes(params, NumberMeta, "int32")

