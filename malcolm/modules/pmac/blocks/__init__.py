from malcolm.yamlutil import make_block_creator, check_yaml_names

brick_block = make_block_creator(__file__, "brick_block.yaml")
compound_motor_block = make_block_creator(__file__, "compound_motor_block.yaml")
cs_block = make_block_creator(__file__, "cs_block.yaml")
pmac_trajectory_block = make_block_creator(
    __file__, "pmac_trajectory_block.yaml")
raw_motor_block = make_block_creator(__file__, "raw_motor_block.yaml")

__all__ = check_yaml_names(globals())
