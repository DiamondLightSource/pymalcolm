from malcolm.yamlutil import make_block_creator, check_yaml_names

shutter_block = make_block_creator(__file__, "shutter_block.yaml")
scan_runner_block = make_block_creator(__file__, "scan_runner_block.yaml")
attribute_block = make_block_creator(__file__, "attribute_block.yaml")

__all__ = check_yaml_names(globals())
