from malcolm.yamlutil import make_block_creator

pandablocks_runnable_block = make_block_creator(
    __file__, "pandablocks_runnable_block.yaml")

del make_block_creator
