from malcolm.yamlutil import check_yaml_names, make_block_creator

ADAndor3_driver_block = make_block_creator(__file__, "ADAndor3_driver_block.yaml")
ADAndor3_runnable_block = make_block_creator(__file__, "ADAndor3_runnable_block.yaml")

__all__ = check_yaml_names(globals())
