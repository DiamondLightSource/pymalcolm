from malcolm.yamlutil import make_block_creator, check_yaml_names

excalibur_detector_driver_block = make_block_creator(
    __file__, "excalibur_detector_driver_block.yaml")

excalibur_detector_runnable_block = make_block_creator(
    __file__, "excalibur_detector_runnable_block.yaml")

fem_detector_driver_block = make_block_creator(
    __file__, "fem_detector_driver_block.yaml")

fem_detector_runnable_block = make_block_creator(
    __file__, "fem_detector_runnable_block.yaml")

gap_plugin_block = make_block_creator(
    __file__, "gap_plugin_block.yaml")
    
excalibur_munge_block = make_block_creator(
    __file__, "excalibur_munge_block.yaml")

__all__ = check_yaml_names(globals())
