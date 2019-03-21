import re

CAMEL_RE = re.compile(r"[a-z][a-z0-9]*([A-Z][a-z0-9]*)*$")


def camel_to_title(name):
    """Takes a camelCaseFieldName and returns an Title Case Field Name

    Args:
        name (str): E.g. camelCaseFieldName

    Returns:
        str: Title Case converted name. E.g. Camel Case Field Name
    """
    split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)", name)
    ret = " ".join(split)
    ret = ret[0].upper() + ret[1:]
    return ret


def snake_to_camel(name):
    """Takes a snake_field_name and returns a camelCaseFieldName

    Args:
        name (str): E.g. snake_field_name or SNAKE_FIELD_NAME

    Returns:
        str: camelCase converted name. E.g. capsFieldName
    """
    ret = "".join(x.title() for x in name.split("_"))
    ret = ret[0].lower() + ret[1:]
    return ret



