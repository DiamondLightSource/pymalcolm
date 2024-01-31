from malcolm.yamlutil import check_yaml_names, make_include_creator

panda_adbase_parts = make_include_creator(__file__, "panda_adbase_parts.yaml")

__all__ = check_yaml_names(globals())
