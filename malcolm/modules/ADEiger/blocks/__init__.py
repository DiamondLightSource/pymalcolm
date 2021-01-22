from malcolm.yamlutil import check_yaml_names, make_block_creator

eiger_driver_block = make_block_creator(__file__, "eiger_driver_block.yaml")
eiger_runnable_block = make_block_creator(__file__, "eiger_runnable_block.yaml")

__all__ = check_yaml_names(globals())
