from malcolm.yamlutil import check_yaml_names, make_block_creator

panda_manager_block = make_block_creator(__file__, "panda_manager_block.yaml")

__all__ = check_yaml_names(globals())
