from malcolm.yamlutil import check_yaml_names, make_block_creator

shutter_block = make_block_creator(__file__, "shutter_block.yaml")
scan_runner_block = make_block_creator(__file__, "scan_runner_block.yaml")
attribute_block = make_block_creator(__file__, "attribute_block.yaml")
directory_monitor_block = make_block_creator(__file__, "directory_monitor_block.yaml")

__all__ = check_yaml_names(globals())
