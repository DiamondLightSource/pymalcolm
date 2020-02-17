from malcolm.yamlutil import make_block_creator, check_yaml_names

adpilatus_driver_block = make_block_creator(
    __file__, " ADPilatus_driver_block.yaml")
adpilatus_runnable_block = make_block_creator(
    __file__, "ADPilatus_runnable_block.yaml")

__all__ = check_yaml_names(globals())
