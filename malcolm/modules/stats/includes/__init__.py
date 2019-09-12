from malcolm.yamlutil import make_include_creator, check_yaml_names

stats_collection = make_include_creator(__file__, "stats_collection.yaml")

__all__ = check_yaml_names(globals())
