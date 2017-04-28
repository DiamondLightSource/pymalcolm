from malcolm.yamlutil import make_block_creator, check_yaml_names

iO8_det_scan_combined_block = make_block_creator(
    __file__, "i08_det_scan_combined_block.yaml")

i08_pamc_manager_block = make_block_creator(
    __file__, "i08_pmac_manager_block.yaml")

i08_scan_butterfly_block = make_block_creator(
    __file__, "i08_scan_butterfly_block.yaml")

i08_two_det_scan_combined_block = make_block_creator(
    __file__, "i08_two_det_scan_combined_block.yaml")

check_yaml_names(globals())
