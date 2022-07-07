from malcolm.yamlutil import check_yaml_names, make_block_creator

tucsen_driver_block = make_block_creator(__file__, "tucsen_driver_block.yaml")

tucsen_runnable_block = make_block_creator(__file__, "tucsen_runnable_block.yaml")

__all__ = check_yaml_names(globals())
