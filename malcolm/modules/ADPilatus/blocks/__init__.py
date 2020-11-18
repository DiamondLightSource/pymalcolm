from malcolm.yamlutil import check_yaml_names, make_block_creator

ADPilatus_driver_block = make_block_creator(__file__, "ADPilatus_driver_block.yaml")
ADPilatus_runnable_block = make_block_creator(__file__, "ADPilatus_runnable_block.yaml")

__all__ = check_yaml_names(globals())
