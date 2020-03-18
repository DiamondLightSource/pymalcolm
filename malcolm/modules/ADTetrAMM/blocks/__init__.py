from malcolm.yamlutil import make_block_creator, check_yaml_names

tetrAMM_driver_block = make_block_creator(__file__, "tetrAMM_driver_block.yaml")
tetrAMM_runnable_block = make_block_creator(__file__, "tetrAMM_runnable_block.yaml")

__all__ = check_yaml_names(globals())
