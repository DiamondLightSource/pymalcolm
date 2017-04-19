from malcolm.yamlutil import make_block_creator

profiling_block = make_block_creator(__file__, "profiling_block.yaml")
profiling_web_server_block = make_block_creator(
    __file__, "profiling_web_server_block.yaml")

del make_block_creator
