from malcolm.yamlutil import make_block_creator, check_yaml_names

pandablocks_manager_block = make_block_creator(
    __file__, "pandablocks_manager_block.yaml")

__all__ = check_yaml_names(globals())
