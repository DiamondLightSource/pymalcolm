from malcolm.yamlutil import check_yaml_names, make_block_creator

zebra_driver_block = make_block_creator(__file__, "zebra_driver_block.yaml")
zebra_runnable_block = make_block_creator(__file__, "zebra_runnable_block.yaml")

__all__ = check_yaml_names(globals())
