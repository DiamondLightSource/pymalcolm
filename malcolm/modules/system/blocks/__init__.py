from malcolm.yamlutil import check_yaml_names, make_block_creator

system_block = make_block_creator(__file__, "system_block.yaml")

__all__ = check_yaml_names(globals())
