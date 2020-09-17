from malcolm.yamlutil import check_yaml_names, make_block_creator

andor_driver_block = make_block_creator(__file__, "andor_driver_block.yaml")

andor_runnable_block = make_block_creator(__file__, "andor_runnable_block.yaml")

__all__ = check_yaml_names(globals())
