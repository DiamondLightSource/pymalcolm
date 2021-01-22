from malcolm.yamlutil import check_yaml_names, make_block_creator

tetrAMM_driver_block = make_block_creator(__file__, "tetrAMM_driver_block.yaml")
tetrAMM_runnable_block = make_block_creator(__file__, "tetrAMM_runnable_block.yaml")

__all__ = check_yaml_names(globals())
