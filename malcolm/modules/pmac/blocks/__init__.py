from malcolm.yamlutil import check_yaml_names, make_block_creator

compound_motor_block = make_block_creator(__file__, "compound_motor_block.yaml")
cs_block = make_block_creator(__file__, "cs_block.yaml")
pmac_status_block = make_block_creator(__file__, "pmac_status_block.yaml")
pmac_trajectory_block = make_block_creator(__file__, "pmac_trajectory_block.yaml")
raw_motor_block = make_block_creator(__file__, "raw_motor_block.yaml")

__all__ = check_yaml_names(globals())
