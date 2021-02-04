from malcolm.yamlutil import check_yaml_names, make_block_creator

xspress3_driver_block = make_block_creator(__file__, "xspress3_driver_block.yaml")
xspress3_dtc_block = make_block_creator(__file__, "xspress3_dtc_block.yaml")
xspress3_runnable_block = make_block_creator(__file__, "xspress3_runnable_block.yaml")

__all__ = check_yaml_names(globals())
