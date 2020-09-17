from malcolm.yamlutil import check_yaml_names, make_block_creator

reframe_plugin_block = make_block_creator(__file__, "reframe_plugin_block.yaml")

__all__ = check_yaml_names(globals())
