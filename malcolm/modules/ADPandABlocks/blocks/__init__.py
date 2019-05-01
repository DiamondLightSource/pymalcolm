from malcolm.yamlutil import make_block_creator, check_yaml_names

panda_exposure_block = make_block_creator(__file__, "panda_exposure_block.yaml")
panda_runnable_block = make_block_creator(__file__, "panda_runnable_block.yaml")
panda_pcomp_block = make_block_creator(__file__, "panda_pcomp_block.yaml")

__all__ = check_yaml_names(globals())
