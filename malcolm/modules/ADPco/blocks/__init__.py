from malcolm.yamlutil import make_block_creator, check_yaml_names

pco_driver_block = make_block_creator(
    __file__, "pco_driver_block.yaml")
pco_runnable_block = make_block_creator(
    __file__, "pco_runnable_block.yaml")

__all__ = check_yaml_names(globals())