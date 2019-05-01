from malcolm.yamlutil import make_block_creator, check_yaml_names

panda_manager_block = make_block_creator(__file__, "panda_manager_block.yaml")

__all__ = check_yaml_names(globals())
