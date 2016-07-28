def load_from_yaml(text):
    import ruamel.yaml
    # TODO: support poyo too as it's pure python...
    data = ruamel.yaml.load(text, ruamel.yaml.RoundTripLoader)
    return data

def with_takes_from(ds):
    # find all the Takes objects and create them
    takes_arguments = []
    for typeid in ds.items():
        if typeid.startswith("takes."):
            d["typeid"] = typeid
            take = Serializable.from_dict(d)
            takes_arguments += [take.make_meta(), take.default]
    return takes(takes_arguments)

def make_subclass(text):
    ds = load_from_yaml(text)

    @with_takes_from(ds)
    class Tmp(Block):
        pass



