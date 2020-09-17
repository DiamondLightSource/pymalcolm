from malcolm.yamlutil import check_yaml_names, make_block_creator

xmap_driver_block = make_block_creator(__file__, "xmap_driver_block.yaml")
xmap_runnable_block = make_block_creator(__file__, "xmap_runnable_block.yaml")

__all__ = check_yaml_names(globals())
