from malcolm.yamlutil import make_block_creator, check_yaml_names

pva_server_block = make_block_creator(__file__, "pva_server_block.yaml")
pva_client_block = make_block_creator(__file__, "pva_client_block.yaml")

__all__ = check_yaml_names(globals())
