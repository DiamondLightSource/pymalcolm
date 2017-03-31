from malcolm.yamlutil import make_block_creator

counter_block = make_block_creator(__file__, "counter_block.yaml")
hello_block = make_block_creator(__file__, "hello_block.yaml")
ticker_block = make_block_creator(__file__, "ticker_block.yaml")

del make_block_creator
