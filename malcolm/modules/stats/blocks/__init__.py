from malcolm.yamlutil import make_block_creator, check_yaml_names

dev_malcolm_stats_block = make_block_creator(__file__, "stats_block.yaml")

__all__ = check_yaml_names(globals())
