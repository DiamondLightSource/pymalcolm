from malcolm.yamlutil import check_yaml_names, make_block_creator

dummy_block = make_block_creator(__file__, "dummy_block.yaml")

__all__ = check_yaml_names(globals())
