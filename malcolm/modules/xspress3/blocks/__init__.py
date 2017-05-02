from malcolm.yamlutil import make_block_creator, check_yaml_names

xspress3_detector_driver_block = make_block_creator(
    __file__, "xspress3_detector_driver_block.yaml")

xspress3_detector_manager_block = make_block_creator(
    __file__, "xspress3_detector_manager_block.yaml")

check_yaml_names(globals())
