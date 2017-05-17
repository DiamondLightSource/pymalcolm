from malcolm.yamlutil import make_block_creator, check_yaml_names

pandablocks_runnable_block = make_block_creator(
    __file__, "pandablocks_runnable_block.yaml")

__all__ = check_yaml_names(globals())
