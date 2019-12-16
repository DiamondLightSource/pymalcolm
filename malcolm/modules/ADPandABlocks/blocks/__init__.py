from malcolm.yamlutil import make_block_creator, check_yaml_names

panda_exposure_block = make_block_creator(__file__, "panda_exposure_block.yaml")
panda_runnable_block = make_block_creator(__file__, "panda_runnable_block.yaml")
panda_seq_trigger_block = make_block_creator(
    __file__, "panda_seq_trigger_block.yaml")
panda_pulse_trigger_block = make_block_creator(
    __file__, "panda_pulse_trigger_block.yaml")
panda_alternating_div_block = make_block_creator(
    __file__, "panda_alternating_div_block.yaml")

__all__ = check_yaml_names(globals())
