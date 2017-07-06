from malcolm.yamlutil import make_block_creator, check_yaml_names

reframe_plugin_block = make_block_creator(
    __file__, "reframe_plugin_block.yaml")

__all__ = check_yaml_names(globals())
