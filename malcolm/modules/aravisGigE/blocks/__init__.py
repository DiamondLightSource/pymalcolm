from malcolm.yamlutil import check_yaml_names, make_block_creator

aravisGigE_driver_block = make_block_creator(__file__, "aravisGigE_driver_block.yaml")
aravisGigE_runnable_block = make_block_creator(
    __file__, "aravisGigE_runnable_block.yaml"
)
aravisGigE_manager_block = make_block_creator(__file__, "aravisGigE_manager_block.yaml")

__all__ = check_yaml_names(globals())
