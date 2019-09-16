from malcolm.yamlutil import make_block_creator, check_yaml_names

stats_block = make_block_creator(__file__, "stats_block.yaml")
stats_block_w_servers = make_block_creator(__file__,
                                           "stats_block_w_servers.yaml")

__all__ = check_yaml_names(globals())
