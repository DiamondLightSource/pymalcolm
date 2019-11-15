from malcolm.yamlutil import make_block_creator, check_yaml_names

shutter_block = make_block_creator(__file__, "shutter_block.yaml")

__all__ = check_yaml_names(globals())
