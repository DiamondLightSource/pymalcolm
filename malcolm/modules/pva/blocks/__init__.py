from malcolm.yamlutil import make_block_creator

pva_server_block = make_block_creator(__file__, "pva_server_block.yaml")
pva_client_block = make_block_creator(__file__, "pva_client_block.yaml")

del make_block_creator
