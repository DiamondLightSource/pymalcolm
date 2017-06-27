from malcolm.yamlutil import make_block_creator, check_yaml_names

pmac_runnable_block = make_block_creator(__file__, "pmac_runnable_block.yaml")
xspress3_scan_block = make_block_creator(__file__, "xspress3_scan_block.yaml")

__all__ = check_yaml_names(globals())

