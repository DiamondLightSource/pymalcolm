from malcolm.yamlutil import make_block_creator, check_yaml_names

dtacq_driver_block = make_block_creator(
    __file__, "dtacq_driver_block.yaml")
dtacq_runnable_block = make_block_creator(
    __file__, "dtacq_runnable_block.yaml")

__all__ = check_yaml_names(globals())
