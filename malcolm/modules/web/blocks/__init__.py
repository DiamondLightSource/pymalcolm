from malcolm.yamlutil import make_block_creator, check_yaml_names

web_server_block = make_block_creator(__file__, "web_server_block.yaml")
websocket_client_block = make_block_creator(
    __file__, "websocket_client_block.yaml")

__all__ = check_yaml_names(globals())
