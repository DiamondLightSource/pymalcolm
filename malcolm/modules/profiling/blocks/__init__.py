from malcolm.yamlutil import check_yaml_names, make_block_creator

profiling_web_server_block = make_block_creator(
    __file__, "profiling_web_server_block.yaml"
)

__all__ = check_yaml_names(globals())
