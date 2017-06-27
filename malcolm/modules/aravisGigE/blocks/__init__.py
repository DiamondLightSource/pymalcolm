from malcolm.yamlutil import make_block_creator, check_yaml_names

aravisGigE_driver_block = make_block_creator(
    __file__, "aravisGigE_driver_block.yaml")
aravisGigE_runnable_block = make_block_creator(
    __file__, "aravisGigE_runnable_block.yaml")

__all__ = check_yaml_names(globals())
