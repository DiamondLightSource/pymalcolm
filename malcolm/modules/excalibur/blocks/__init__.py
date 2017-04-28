from malcolm.yamlutil import make_block_creator, check_yaml_names

excalibur_detector_driver_block = make_block_creator(
    __file__, "excalibur_detector_driver_block.yaml")

excalibur_detector_manager_block = make_block_creator(
    __file__, "excalibur_detector_manager_block.yaml")

fem_detector_driver_block = make_block_creator(
    __file__, "fem_detector_driver_block.yaml")

fem_detector_manager_block = make_block_creator(
    __file__, "fem_detector_manager_block.yaml")

check_yaml_names(globals())
