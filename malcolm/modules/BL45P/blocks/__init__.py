from malcolm.yamlutil import make_block_creator, check_yaml_names

hardware_scan_block = make_block_creator(__file__, "hardware_scan_block.yaml")
pmac_manager_block = make_block_creator(__file__, "pmac_manager_block.yaml")
sim_scan_block = make_block_creator(__file__, "sim_scan_block.yaml")

check_yaml_names(globals())
