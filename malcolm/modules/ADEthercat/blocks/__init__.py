from malcolm.yamlutil import check_yaml_names, make_block_creator

ethercat_driver_block = make_block_creator(__file__, "ethercat_driver_block.yaml")
ethercat_reframe_block = make_block_creator(__file__, "ethercat_reframe_block.yaml")
ethercat_continuous_block = make_block_creator(__file__, "ethercat_continuous_block.yaml")

__all__ = check_yaml_names(globals())
