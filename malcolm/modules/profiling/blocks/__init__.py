from malcolm.yamlutil import make_block_creator, check_yaml_names

profiling_web_server_block = make_block_creator(
    __file__, "profiling_web_server_block.yaml")

check_yaml_names(globals())
