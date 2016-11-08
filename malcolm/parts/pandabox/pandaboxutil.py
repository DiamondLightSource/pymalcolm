def make_label_attr_name(field_name):
    """Takes a field_name and returns label with spaces and camelCase attr_name

    Args:
        field_name (str): E.g. OUT_VALUE.DATA_DELAY

    Returns:
        tuple: (label, attr_name). E.g.
            ("Out Value Data Delay", "outValueDataDelay")
    """
    label = field_name.replace(".", " ").replace("_", " ").title()
    attr_name = label.replace(" ", "")
    attr_name = attr_name[0].lower() + attr_name[1:]
    return label, attr_name
