from malcolm.yamlutil import make_block_creator, check_yaml_names

zebra_driver_block = make_block_creator(
    __file__, "zebra_driver_block.yaml")
zebra_runnable_block = make_block_creator(
    __file__, "zebra_runnable_block.yaml")

__all__ = check_yaml_names(globals())
