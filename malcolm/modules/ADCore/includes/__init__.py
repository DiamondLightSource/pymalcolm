from malcolm.yamlutil import check_yaml_names, make_include_creator

adbase_parts = make_include_creator(__file__, "adbase_parts.yaml")
filewriting_collection = make_include_creator(__file__, "filewriting_collection.yaml")
ndarraybase_parts = make_include_creator(__file__, "ndarraybase_parts.yaml")
ndpluginbase_parts = make_include_creator(__file__, "ndpluginbase_parts.yaml")

__all__ = check_yaml_names(globals())
