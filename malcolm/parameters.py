from malcolm.core.method import takes, REQUIRED, OPTIONAL
from malcolm.metas import StringMeta, NumberMeta


def takes_with_default_meta(meta_cls, *meta_args):
    default_args = (
        "default", "Default value for parameter. If not specified, "
        "parameter is required") + meta_args
    return takes(
        StringMeta("name",
                   "Specify that this class will take a parameter name"),
        REQUIRED,
        StringMeta("description", "Description of this parameter"),
        REQUIRED,
        meta_cls(*default_args),
        OPTIONAL)


def args_for_takes(params, meta_cls, *meta_args):
    meta_args = (params.name, params.description) + meta_args
    meta = meta_cls(*meta_args)
    if hasattr(params, "default"):
        return [meta, params.default]
    else:
        return [meta, REQUIRED]


@takes_with_default_meta(StringMeta)
def string(params):
    return args_for_takes(params, StringMeta)


@takes_with_default_meta(NumberMeta, "float64")
def float64(params):
    return args_for_takes(params, NumberMeta, "float64")


@takes_with_default_meta(NumberMeta, "int32")
def int32(params):
    return args_for_takes(params, NumberMeta, "int32")
