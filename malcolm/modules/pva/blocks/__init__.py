from malcolm.yamlutil import check_yaml_names, make_block_creator

pva_server_block = make_block_creator(__file__, "pva_server_block.yaml")
pva_client_block = make_block_creator(__file__, "pva_client_block.yaml")

__all__ = check_yaml_names(globals())
