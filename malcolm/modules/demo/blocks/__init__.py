from malcolm.yamlutil import make_block_creator, check_yaml_names

counter_block = make_block_creator(__file__, "counter_block.yaml")
hello_block = make_block_creator(__file__, "hello_block.yaml")
motion_block = make_block_creator(__file__, "motion_block.yaml")
detector_block = make_block_creator(__file__, "detector_block.yaml")
scan_1det_block = make_block_creator(__file__, "scan_1det_block.yaml")
scan_2det_block = make_block_creator(__file__, "scan_2det_block.yaml")

__all__ = check_yaml_names(globals())
