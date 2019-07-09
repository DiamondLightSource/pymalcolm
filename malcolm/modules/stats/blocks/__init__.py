from malcolm.yamlutil import make_block_creator, check_yaml_names

stats_block = make_block_creator(__file__, "stats_block.yaml")
ioc_status_block = make_block_creator(__file__, "ioc_status_block.yaml")
wrapper_block = make_block_creator(__file__, "wrapper_block.yaml")

__all__ = check_yaml_names(globals())
