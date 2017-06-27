from malcolm.yamlutil import make_include_creator, check_yaml_names

adbase_parts = make_include_creator(
    __file__, "adbase_parts.yaml")
filewriting_collection = make_include_creator(
    __file__, "filewriting_collection.yaml")
ndarraybase_parts = make_include_creator(
    __file__, "ndarraybase_parts.yaml")
ndpluginbase_parts = make_include_creator(
    __file__, "ndpluginbase_parts.yaml")

__all__ = check_yaml_names(globals())
