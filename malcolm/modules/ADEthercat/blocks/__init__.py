from malcolm.yamlutil import check_yaml_names, make_block_creator

ethercat_driver_block = make_block_creator(__file__, "ethercat_driver_block.yaml")
ethercat_runnable_block = make_block_creator(__file__, "ethercat_runnable_block.yaml")

__all__ = check_yaml_names(globals())
