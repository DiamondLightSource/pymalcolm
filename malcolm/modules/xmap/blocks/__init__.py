from malcolm.yamlutil import make_block_creator, check_yaml_names

xmap_detector_driver_block = make_block_creator(
    __file__, "xmap_detector_driver_block.yaml")

xmap_detector_manager_block = make_block_creator(
    __file__, "xmap_detector_manager_block.yaml")

__all__ = check_yaml_names(globals())
