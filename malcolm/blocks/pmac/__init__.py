from malcolm.yamlutil import make_block_creator

compound_motor_block = make_block_creator(__file__, "compound_motor_block.yaml")
pmac_trajectory_block = make_block_creator(
    __file__, "pmac_trajectory_block.yaml")
raw_motor_block = make_block_creator(__file__, "raw_motor_block.yaml")

del make_block_creator
