from malcolm.yamlutil import check_yaml_names, make_block_creator

merlin_driver_block = make_block_creator(__file__, "merlin_driver_block.yaml")

merlin_runnable_block = make_block_creator(__file__, "merlin_runnable_block.yaml")

__all__ = check_yaml_names(globals())
